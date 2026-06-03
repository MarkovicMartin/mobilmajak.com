"""
Docházka – sdílená logika stavu, automatické ukončení po 20:30 a přehled chybějících příchodů.

Integrace kamer (Hikvision / HiLook): viz modul camera_integration – bez veřejného RTSP v aplikaci.
"""
from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Smena, SmenaDochazka

AUTO_CLOSE_NOTE = 'Automatické ukončení po 20:30'
AUTO_CLOSE_TIME = time(20, 30)


def local_now():
    return timezone.localtime(timezone.now())


def auto_close_cutoff(datum):
    """Čas automatického odchodu pro daný den směny (lokální TZ)."""
    loc = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(datum, AUTO_CLOSE_TIME), loc)


def attendance_state_from_history(history):
    """
    Stav docházky z historie akcí.
    Vrací (stav, prichod_record, odchod_record).
    stav: bez_zaznamu | otevreno | uzavreno | pauza
    """
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


def has_prichod(history):
    return any(d.typ_akce == 'prichod' for d in history)


def shift_window(smena):
    loc = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(smena.datum, smena.cas_od), loc)
    end = timezone.make_aware(datetime.combine(smena.datum, smena.cas_do), loc)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def shift_is_active_now(smena, now=None):
    """Směna právě probíhá (dnes, mezi cas_od a cas_do)."""
    now = now or local_now()
    if smena.datum != now.date():
        return False
    start, end = shift_window(smena)
    return start <= now <= end


def _already_auto_closed(smena):
    return SmenaDochazka.objects.filter(
        smena=smena,
        typ_akce='odchod',
        poznamka__startswith=AUTO_CLOSE_NOTE,
    ).exists()


def ensure_auto_close_shift(smena, now=None):
    """
    Pokud je docházka otevřená a už je po 20:30 v den směny, zapíše automatický odchod.
    Vrací True pokud byl záznam vytvořen.
    """
    now = now or local_now()
    history = list(smena.dochazka.order_by('cas'))
    stav, _prichod, _odchod = attendance_state_from_history(history)
    if stav != 'otevreno':
        return False
    cutoff = auto_close_cutoff(smena.datum)
    if now < cutoff:
        return False
    if _already_auto_closed(smena):
        return False
    SmenaDochazka.objects.create(
        smena=smena,
        typ_akce='odchod',
        cas=cutoff,
        poznamka=AUTO_CLOSE_NOTE,
    )
    return True


def ensure_auto_close_open_shifts(*, user=None, max_days_back=2):
    """Uzavře všechny otevřené směny po lhůtě 20:30 (volitelně jen pro jednoho uživatele)."""
    now = local_now()
    today = now.date()
    qs = Smena.objects.filter(
        typ_smeny='prace',
        aktivni=True,
        datum__gte=today - timedelta(days=max_days_back),
        datum__lte=today,
    ).prefetch_related('dochazka')
    if user is not None:
        qs = qs.filter(user=user)
    closed = 0
    for smena in qs:
        if ensure_auto_close_shift(smena, now=now):
            closed += 1
    return closed


def build_absent_stores_report(now=None):
    """
    Prodejny, kde právě běží směna ale žádný zaměstnanec nezaklikl příchod.
    """
    now = now or local_now()
    today = now.date()
    ensure_auto_close_open_shifts(max_days_back=1)

    smeny = (
        Smena.objects.filter(
            datum=today,
            typ_smeny='prace',
            aktivni=True,
        )
        .select_related('user', 'prodejna')
        .prefetch_related('dochazka')
    )

    stores = {}
    for smena in smeny:
        if not shift_is_active_now(smena, now):
            continue
        pid = smena.prodejna_id
        if pid not in stores:
            stores[pid] = {
                'prodejna_id': pid,
                'prodejna_nazev': smena.prodejna.nazev_kratkiy or smena.prodejna.nazev,
                'prodejna_barva': smena.prodejna.barva or '#0066cc',
                'active_shifts': [],
                'missing_shifts': [],
                'present_shifts': [],
            }
        history = list(smena.dochazka.all())
        stav, prichod, _odchod = attendance_state_from_history(history)
        entry = {
            'smena_id': smena.id,
            'user_id': smena.user_id,
            'jmeno': f'{smena.user.jmeno} {smena.user.prijmeni}'.strip(),
            'plan_od': smena.cas_od.strftime('%H:%M'),
            'plan_do': smena.cas_do.strftime('%H:%M'),
            'stav': stav,
            'prichod': prichod.cas.strftime('%H:%M') if prichod else None,
        }
        stores[pid]['active_shifts'].append(entry)
        if stav == 'otevreno':
            stores[pid]['present_shifts'].append(entry)
        elif not has_prichod(history):
            stores[pid]['missing_shifts'].append(entry)

    absent = []
    ok_stores = []
    for data in sorted(stores.values(), key=lambda x: x['prodejna_nazev']):
        if data['missing_shifts']:
            data['status'] = 'absent'
            absent.append(data)
        elif data['active_shifts']:
            data['status'] = 'ok'
            ok_stores.append(data)

    return {
        'checked_at': now.isoformat(),
        'absent_stores': absent,
        'ok_stores': ok_stores,
        'auto_close_time': AUTO_CLOSE_TIME.strftime('%H:%M'),
    }
