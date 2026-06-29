"""Finance API – všechny endpointy ADMIN-only."""
from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .fio_status import FIO_DISABLED_MESSAGE, get_fio_import_status
from .models import FioKategorizacniPravidlo, NakladKategorie, NakladPolozka
from .permissions import finance_admin_view
from .services import log_finance_audit, serialize_naklad_polozka


def _no_store_response(data, status_code=status.HTTP_200_OK):
    resp = Response(data, status=status_code)
    resp['Cache-Control'] = 'no-store'
    return resp


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def finance_status(request):
    fio = get_fio_import_status()
    log_finance_audit(request, 'status')
    return _no_store_response({
        'fio': {
            'available': fio['available'],
            'enabled': fio['enabled'],
            'message': fio['message'] or FIO_DISABLED_MESSAGE,
        },
        'manual_naklady': True,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklad_kategorie_list(request):
    log_finance_audit(request, 'kategorie_list')
    rows = NakladKategorie.objects.filter(aktivni=True).order_by('poradi', 'nazev')
    return _no_store_response([
        {'id': k.id, 'nazev': k.nazev, 'poradi': k.poradi}
        for k in rows
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklady_nezarazene(request):
    log_finance_audit(request, 'naklady_nezarazene')
    qs = NakladPolozka.objects.filter(stav=NakladPolozka.STAV_NEZARAZENO).select_related('kategorie')
    return _no_store_response([serialize_naklad_polozka(p) for p in qs[:500]])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklad_manual_create(request):
    data = request.data
    try:
        datum = datetime.strptime(data.get('datum', ''), '%Y-%m-%d').date()
        castka = data.get('castka')
        if castka is None or castka == '':
            return _no_store_response({'error': 'Chybí castka'}, status.HTTP_400_BAD_REQUEST)
    except ValueError:
        return _no_store_response({'error': 'Neplatný datum (YYYY-MM-DD)'}, status.HTTP_400_BAD_REQUEST)

    kategorie_id = data.get('kategorie_id') or None
    if kategorie_id:
        try:
            kategorie_id = int(kategorie_id)
        except (TypeError, ValueError):
            return _no_store_response({'error': 'Neplatná kategorie'}, status.HTTP_400_BAD_REQUEST)

    prodejna_id = data.get('prodejna_id')
    if prodejna_id not in (None, ''):
        try:
            prodejna_id = int(prodejna_id)
        except (TypeError, ValueError):
            return _no_store_response({'error': 'Neplatná prodejna'}, status.HTTP_400_BAD_REQUEST)
    else:
        prodejna_id = None

    polozka = NakladPolozka.objects.create(
        datum=datum,
        rok=datum.year,
        mesic=datum.month,
        castka=castka,
        kategorie_id=kategorie_id,
        prodejna_id=prodejna_id,
        stav=NakladPolozka.STAV_ZARAZENO if kategorie_id else NakladPolozka.STAV_NEZARAZENO,
        zdroj=NakladPolozka.ZDROJ_MANUAL,
        popis=(data.get('popis') or '')[:500],
        poznamka_admin=(data.get('poznamka_admin') or '')[:2000],
        upravil_user_id=request.user.id,
        upraveno=timezone.now(),
    )
    log_finance_audit(request, 'naklad_manual_create', f'id={polozka.id}')
    return _no_store_response(serialize_naklad_polozka(polozka), status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklad_update(request, polozka_id):
    try:
        polozka = NakladPolozka.objects.get(pk=polozka_id)
    except NakladPolozka.DoesNotExist:
        return _no_store_response({'error': 'Položka nenalezena'}, status.HTTP_404_NOT_FOUND)

    data = request.data
    if 'kategorie_id' in data:
        kid = data.get('kategorie_id')
        polozka.kategorie_id = int(kid) if kid not in (None, '') else None
    if 'prodejna_id' in data:
        pid = data.get('prodejna_id')
        polozka.prodejna_id = int(pid) if pid not in (None, '') else None
    if 'stav' in data:
        polozka.stav = data['stav']
    if 'ignorovat' in data:
        polozka.ignorovat = bool(data['ignorovat'])
        if polozka.ignorovat:
            polozka.stav = NakladPolozka.STAV_IGNOROVAT
    if 'poznamka_admin' in data:
        polozka.poznamka_admin = (data.get('poznamka_admin') or '')[:2000]

    if data.get('zaradit'):
        if not polozka.kategorie_id:
            return _no_store_response({'error': 'Pro zařazení vyberte kategorii'}, status.HTTP_400_BAD_REQUEST)
        polozka.stav = NakladPolozka.STAV_RUCNE
        polozka.ignorovat = False

    polozka.upravil_user_id = request.user.id
    polozka.upraveno = timezone.now()
    polozka.save()
    log_finance_audit(request, 'naklad_update', f'id={polozka.id}')
    return _no_store_response(serialize_naklad_polozka(polozka))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def pravidlo_create(request):
    data = request.data
    rule = FioKategorizacniPravidlo.objects.create(
        protiucet=(data.get('protiucet') or '')[:64],
        zprava_obsahuje=(data.get('zprava_obsahuje') or '')[:200],
        vs=(data.get('vs') or '')[:32],
        kategorie_id=data.get('kategorie_id') or None,
        prodejna_id=data.get('prodejna_id') or None,
        ignorovat=bool(data.get('ignorovat')),
        vytvoril_user_id=request.user.id,
    )
    log_finance_audit(request, 'pravidlo_create', f'id={rule.id}')
    return _no_store_response({'id': rule.id}, status.HTTP_201_CREATED)
