"""Payroll a docházka – admin API."""
from datetime import date, datetime, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import WebUser

from .models import MzdovaOdmenaMesic, Smena, SmenaDochazka
from .payroll_service import build_payroll_preview


def _require_admin(request):
    if getattr(request.user, 'role', None) != 'ADMIN':
        return Response({'error': 'Nemáte oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    return None


def _parse_mesic(mesic):
    try:
        rok, mesic_cislo = map(int, mesic.split('-'))
        return rok, mesic_cislo, date(rok, mesic_cislo, 1)
    except (ValueError, AttributeError):
        return None


def _attendance_state(history):
    if not history:
        return 'bez_zaznamu', None, None
    sorted_h = sorted(history, key=lambda x: x.cas)
    prichod = next((h for h in sorted_h if h.typ_akce == 'prichod'), None)
    odchod = next((h for h in reversed(sorted_h) if h.typ_akce == 'odchod'), None)
    last = sorted_h[-1]
    if last.typ_akce in ('prichod', 'pauza_konec'):
        stav = 'otevreno'
    elif last.typ_akce == 'odchod':
        stav = 'uzavreno'
    else:
        stav = 'pauza'
    return stav, prichod, odchod


def _compute_work_hours_from_history(history):
    if not history:
        return 0
    total_min = 0
    start = None
    for action in sorted(history, key=lambda x: x.cas):
        t = action.cas
        if action.typ_akce in ('prichod', 'pauza_konec'):
            start = t
        elif action.typ_akce in ('pauza_start', 'odchod') and start:
            total_min += (t - start).total_seconds() / 60
            start = None
    return round(total_min / 60, 2)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_preview(request):
    denied = _require_admin(request)
    if denied:
        return denied
    mesic = request.GET.get('mesic')
    if not mesic:
        return Response({'error': 'Chybí parametr mesic'}, status=status.HTTP_400_BAD_REQUEST)
    if not _parse_mesic(mesic):
        return Response({'error': 'Neplatný formát měsíce'}, status=status.HTTP_400_BAD_REQUEST)
    prodejna = request.GET.get('prodejna')
    data = build_payroll_preview(mesic, prodejna_id=prodejna)
    return Response(data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def payroll_odmena(request):
    denied = _require_admin(request)
    if denied:
        return denied
    user_id = request.data.get('user_id')
    mesic = request.data.get('mesic')
    if not user_id or not mesic:
        return Response({'error': 'Chybí user_id nebo mesic'}, status=status.HTTP_400_BAD_REQUEST)
    parsed = _parse_mesic(mesic)
    if not parsed:
        return Response({'error': 'Neplatný formát měsíce'}, status=status.HTTP_400_BAD_REQUEST)
    _, _, mesic_date = parsed
    try:
        castka = float(request.data.get('castka') or 0)
    except (TypeError, ValueError):
        return Response({'error': 'Neplatná castka'}, status=status.HTTP_400_BAD_REQUEST)
    if castka < 0:
        castka = 0
    poznamka = (request.data.get('poznamka') or '').strip()
    pridat = request.data.get('add') in (True, 'true', '1', 1)
    user = WebUser.objects.filter(id=user_id).first()
    if not user:
        return Response({'error': 'Uživatel nenalezen'}, status=status.HTTP_404_NOT_FOUND)
    existing = MzdovaOdmenaMesic.objects.filter(user=user, mesic=mesic_date).first()
    if pridat and existing:
        nova_castka = float(existing.castka) + castka
        if poznamka and existing.poznamka:
            poznamka = f'{existing.poznamka}; {poznamka}'
        elif not poznamka:
            poznamka = existing.poznamka or ''
    else:
        nova_castka = castka
    row, _created = MzdovaOdmenaMesic.objects.update_or_create(
        user=user,
        mesic=mesic_date,
        defaults={'castka': nova_castka, 'poznamka': poznamka},
    )
    return Response({
        'user_id': user.id,
        'mesic': mesic,
        'odmena_mesic_body': float(row.castka),
        'poznamka': row.poznamka,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_log(request):
    denied = _require_admin(request)
    if denied:
        return denied
    mesic = request.GET.get('mesic')
    if not mesic:
        return Response({'error': 'Chybí parametr mesic'}, status=status.HTTP_400_BAD_REQUEST)
    parsed = _parse_mesic(mesic)
    if not parsed:
        return Response({'error': 'Neplatný formát měsíce'}, status=status.HTTP_400_BAD_REQUEST)
    rok, mesic_cislo, _ = parsed
    today = date.today()
    tolerance_min = 30

    smeny = Smena.objects.filter(
        datum__year=rok,
        datum__month=mesic_cislo,
        typ_smeny='prace',
        aktivni=True,
    ).select_related('user', 'prodejna').prefetch_related('dochazka')

    entries = []
    for smena in smeny.order_by('-datum', 'user__prijmeni'):
        history = list(smena.dochazka.all())
        stav, prichod, odchod = _attendance_state(history)
        plan_od = datetime.combine(smena.datum, smena.cas_od)
        plan_do = datetime.combine(smena.datum, smena.cas_do)
        if plan_do < plan_od:
            plan_do += timedelta(days=1)

        problem = False
        problem_duvod = ''
        if stav == 'otevreno':
            if smena.datum < today:
                problem = True
                problem_duvod = 'zapomenuty_odchod'
            elif timezone.now() > plan_do + timedelta(minutes=tolerance_min):
                problem = True
                problem_duvod = 'po_konci_smeny_bez_odchodu'
        elif stav == 'bez_zaznamu' and smena.datum < today:
            problem = True
            problem_duvod = 'zadna_dochazka'

        if prichod:
            konec_od = prichod.cas.strftime('%H:%M')
        else:
            konec_od = plan_od.strftime('%H:%M')
        if odchod:
            konec_do = odchod.cas.strftime('%H:%M')
        else:
            konec_do = 'otevřeno' if stav == 'otevreno' else plan_do.strftime('%H:%M')

        entries.append({
            'smena_id': smena.id,
            'user_id': smena.user_id,
            'jmeno': f'{smena.user.jmeno} {smena.user.prijmeni}'.strip(),
            'datum': smena.datum.isoformat(),
            'prodejna': smena.prodejna.nazev,
            'plan_od': smena.cas_od.strftime('%H:%M'),
            'plan_do': smena.cas_do.strftime('%H:%M'),
            'cas_rozsah_od': konec_od,
            'cas_rozsah_do': konec_do,
            'stav': stav,
            'problem': problem,
            'problem_duvod': problem_duvod,
            'hodiny_z_dochozky': _compute_work_hours_from_history(history),
            'akce': [
                {
                    'typ_akce': d.typ_akce,
                    'cas': d.cas.isoformat(),
                }
                for d in sorted(history, key=lambda x: x.cas)
            ],
        })

    return Response({
        'mesic': mesic,
        'entries': entries,
        'problemy_count': sum(1 for e in entries if e['problem']),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_open(request):
    denied = _require_admin(request)
    if denied:
        return denied
    today = date.today()
    smeny = Smena.objects.filter(
        datum__lte=today,
        typ_smeny='prace',
        aktivni=True,
    ).select_related('user', 'prodejna').prefetch_related('dochazka')

    open_list = []
    for smena in smeny:
        history = list(smena.dochazka.all())
        stav, prichod, odchod = _attendance_state(history)
        if stav != 'otevreno':
            continue
        open_list.append({
            'smena_id': smena.id,
            'user_id': smena.user_id,
            'jmeno': f'{smena.user.jmeno} {smena.user.prijmeni}'.strip(),
            'datum': smena.datum.isoformat(),
            'prodejna': smena.prodejna.nazev,
            'prichod': prichod.cas.isoformat() if prichod else None,
            'plan_do': smena.cas_do.strftime('%H:%M'),
        })
    return Response({'open': open_list})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_my_status(request):
    """Stav docházky pro přihlášeného – upozornění na zapomenutý odchod."""
    user = request.user
    today = date.today()
    yesterday = today - timedelta(days=1)

    warnings = []
    for day in (yesterday, today):
        smeny = Smena.objects.filter(
            user=user,
            datum=day,
            typ_smeny='prace',
            aktivni=True,
        ).prefetch_related('dochazka')
        for smena in smeny:
            history = list(smena.dochazka.all())
            stav, prichod, _odchod = _attendance_state(history)
            if stav != 'otevreno':
                continue
            plan_do = datetime.combine(smena.datum, smena.cas_do)
            plan_od = datetime.combine(smena.datum, smena.cas_od)
            if plan_do < plan_od:
                plan_do += timedelta(days=1)
            if day < today or timezone.now() > plan_do:
                warnings.append({
                    'typ': 'zapomenuty_odchod',
                    'datum': smena.datum.isoformat(),
                    'smena_id': smena.id,
                    'zprava': f'Chybí odchod ze směny {smena.datum.strftime("%d.%m.%Y")}',
                })

    return Response({'warnings': warnings})
