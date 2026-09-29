"""API návrhů směn na jiné prodejně."""

from datetime import datetime

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from shifts.models import VyjezdNavrh, VyjezdNotifikace
from shifts.vyjezd import (
    VyjezdChyba,
    dopln_vyjezdy,
    moje_skupiny,
    notifikuj_zmenu,
    over_manualni_zmenu,
    potvrdit_navrh,
    seznam_mesice,
)
from stores.models import Prodejna


def _can_manage(user) -> bool:
    return getattr(user, 'role', None) in ('ADMIN', 'VEDOUCI')


def _parse_mesic(raw):
    try:
        rok, mesic = map(int, (raw or '').split('-'))
        if not 1 <= mesic <= 12:
            raise ValueError
        return rok, mesic
    except (TypeError, ValueError):
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vyjezdy_list(request):
    if not _can_manage(request.user):
        return Response({'error': 'Návrhy upravuje vedoucí.'}, status=status.HTTP_403_FORBIDDEN)
    parsed = _parse_mesic(request.GET.get('mesic'))
    if not parsed:
        return Response({'error': 'Chybí mesic (YYYY-MM).'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(seznam_mesice(*parsed))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vyjezdy_moje(request):
    return Response({'skupiny': moje_skupiny(request.user)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vyjezdy_navrhnout(request):
    if not _can_manage(request.user):
        return Response({'error': 'Návrh zakládá vedoucí.'}, status=status.HTTP_403_FORBIDDEN)
    parsed = _parse_mesic(request.data.get('mesic'))
    if not parsed:
        return Response({'error': 'Chybí mesic (YYYY-MM).'}, status=status.HTTP_400_BAD_REQUEST)
    result = dopln_vyjezdy(*parsed)
    payload = seznam_mesice(*parsed)
    payload['vytvoreno'] = result['vytvoreno']
    return Response(payload)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def vyjezd_detail(request, navrh_id):
    if not _can_manage(request.user):
        return Response({'error': 'Návrh upravuje vedoucí.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        navrh = VyjezdNavrh.objects.select_related('user', 'prodejna').get(pk=navrh_id)
    except VyjezdNavrh.DoesNotExist:
        return Response({'error': 'Návrh nenalezen.'}, status=status.HTTP_404_NOT_FOUND)
    try:
        datum = datetime.strptime(request.data.get('datum') or '', '%Y-%m-%d').date()
        prodejna = Prodejna.objects.get(pk=int(request.data.get('prodejna_id')))
    except (TypeError, ValueError, Prodejna.DoesNotExist):
        return Response({'error': 'Vyplň den a prodejnu.'}, status=status.HTTP_400_BAD_REQUEST)
    changed = navrh.datum != datum or navrh.prodejna_id != prodejna.id
    try:
        over_manualni_zmenu(navrh, datum, prodejna)
    except VyjezdChyba as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    navrh.datum = datum
    navrh.prodejna = prodejna
    navrh.save(update_fields=['datum', 'prodejna', 'upraveno'])
    if changed:
        notifikuj_zmenu(navrh)
    return Response(seznam_mesice(navrh.mesic.year, navrh.mesic.month))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vyjezdy_potvrdit(request):
    if not _can_manage(request.user):
        return Response({'error': 'Směny potvrzuje vedoucí.'}, status=status.HTTP_403_FORBIDDEN)
    ids = request.data.get('ids')
    qs = VyjezdNavrh.objects.filter(stav=VyjezdNavrh.STAV_NAVRH).select_related('user', 'prodejna')
    parsed = _parse_mesic(request.data.get('mesic'))
    if ids:
        qs = qs.filter(id__in=ids)
    elif parsed:
        rok, mesic = parsed
        qs = qs.filter(mesic__year=rok, mesic__month=mesic)
    else:
        return Response({'error': 'Chybí mesic nebo ids.'}, status=status.HTTP_400_BAD_REQUEST)
    vytvoreno = 0
    chyby = []
    for navrh in qs.order_by('datum', 'id'):
        try:
            potvrdit_navrh(navrh)
            vytvoreno += 1
        except VyjezdChyba as exc:
            chyby.append({'id': navrh.id, 'jmeno': navrh.user.prijmeni, 'error': str(exc)})
    payload = {'vytvoreno': vytvoreno, 'chyby': chyby}
    if parsed:
        payload.update(seznam_mesice(*parsed))
    return Response(payload)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vyjezd_notifikace(request):
    qs = VyjezdNotifikace.objects.filter(user=request.user)
    if request.GET.get('read') == '1':
        qs = qs.filter(read_at__isnull=False)
    else:
        qs = qs.filter(read_at__isnull=True)
    data = [
        {
            'id': row.id,
            'message': row.message,
            'mesic': row.mesic.isoformat(),
            'created_at': row.created_at,
            'read_at': row.read_at,
        }
        for row in qs.order_by('-created_at')[:50]
    ]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vyjezd_notifikace_mark_read(request):
    ids = request.data.get('ids')
    qs = VyjezdNotifikace.objects.filter(user=request.user, read_at__isnull=True)
    if ids is not None:
        qs = qs.filter(id__in=ids)
    updated = qs.update(read_at=timezone.now())
    return Response({'marked': updated})
