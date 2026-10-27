"""Finance modul – admin vs. přístup k fakturám na prodejně."""
from datetime import datetime, timedelta
from functools import wraps

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from .models import NakladPolozka, is_bank_zdroj


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def is_finance_admin(user) -> bool:
    return getattr(user, 'role', None) == 'ADMIN'


def naklady_qs_for_invoice_user(qs, user):
    """Běžní uživatelé vidí jen výdeje z pokladny – Fio je jen pro admina."""
    if is_finance_admin(user):
        return qs
    return qs.filter(zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA)


def user_can_upload_doklad(user, polozka) -> bool:
    if not user_can_access_polozka(user, polozka):
        return False
    if not is_finance_admin(user) and is_bank_zdroj(polozka.zdroj):
        return False
    return True


def _local_now(now=None):
    if now is None:
        return timezone.localtime()
    if timezone.is_naive(now):
        return timezone.make_aware(now, timezone.get_current_timezone())
    return timezone.localtime(now)


def _aware(day, clock):
    moment = datetime.combine(day, clock)
    if timezone.is_naive(moment):
        return timezone.make_aware(moment, timezone.get_current_timezone())
    return moment


def _work_shifts(user, days):
    if not user or not getattr(user, 'id', None):
        return []
    from shifts.models import Smena
    return list(
        Smena.objects.filter(
            user_id=user.id,
            datum__in=days,
            aktivni=True,
            typ_smeny='prace',
            prodejna_id__isnull=False,
        ).only('id', 'datum', 'cas_od', 'cas_do', 'prodejna_id')
    )


def today_shift_store_ids(user, now=None) -> list[int]:
    """Prodejny, kde má uživatel dnes pracovní směnu."""
    moment = _local_now(now)
    ids = [int(s.prodejna_id) for s in _work_shifts(user, [moment.date()])]
    return list(dict.fromkeys(ids))


def current_shift_store_id(user, now=None) -> int | None:
    """Prodejna směny, která právě běží (včetně noční z předchozího dne)."""
    moment = _local_now(now)
    days = [moment.date() - timedelta(days=1), moment.date()]
    for smena in _work_shifts(user, days):
        start = _aware(smena.datum, smena.cas_od)
        end = _aware(smena.datum, smena.cas_do)
        if end <= start:
            end += timedelta(days=1)
        if start <= moment <= end:
            return int(smena.prodejna_id)
    return None


def accessible_store_ids(user, now=None) -> list[int] | None:
    """None = všechny prodejny (admin), jinak domácí, vedené a dnešní směny."""
    if getattr(user, 'role', None) == 'ADMIN':
        return None
    ids = []
    if getattr(user, 'prodejna_id', None):
        ids.append(int(user.prodejna_id))
    try:
        from users.vedouci_utils import vedouci_store_ids
        ids.extend(int(x) for x in vedouci_store_ids(user))
    except Exception:
        pass
    ids.extend(today_shift_store_ids(user, now=now))
    current = current_shift_store_id(user, now=now)
    if current:
        ids.append(current)
    return list(dict.fromkeys(ids))


def default_invoice_store_id(user, now=None) -> int | None:
    """Domácí prodejna, dokud neběží směna na jiné. Vedoucí zůstává na všech."""
    if is_finance_admin(user) or getattr(user, 'role', None) == 'VEDOUCI':
        return None
    home = int(user.prodejna_id) if getattr(user, 'prodejna_id', None) else None
    current = current_shift_store_id(user, now=now)
    if current and current != home:
        return current
    if home:
        return home
    if current:
        return current
    ids = accessible_store_ids(user, now=now) or []
    if len(ids) == 1:
        return ids[0]
    return None


def invoice_prodejny_context(user, now=None) -> dict:
    """Prodejny pro přepínač faktur. Admin dostane prodejny=None (vše)."""
    home = int(user.prodejna_id) if getattr(user, 'prodejna_id', None) else None
    current = None if is_finance_admin(user) else current_shift_store_id(user, now=now)
    if is_finance_admin(user):
        return {
            'prodejny': None,
            'default_prodejna_id': None,
            'domaci_prodejna_id': home,
            'aktualni_smena_prodejna_id': None,
        }
    ids = accessible_store_ids(user, now=now) or []
    from stores.models import Prodejna
    rows = list(
        Prodejna.objects.filter(id__in=ids).only('id', 'nazev', 'poradi')
    ) if ids else []
    by_id = {row.id: row for row in rows}

    def sort_key(sid):
        row = by_id.get(sid)
        name = row.nazev if row else ''
        if home and sid == home:
            return (0, 0, name)
        if current and sid == current:
            return (1, 0, name)
        return (2, row.poradi if row else 0, name)

    prodejny = [
        {
            'id': sid,
            'nazev': by_id[sid].nazev if sid in by_id else f'Prodejna {sid}',
            'je_domaci': bool(home and sid == home),
            'je_aktualni_smena': bool(current and sid == current),
        }
        for sid in sorted(ids, key=sort_key)
    ]
    return {
        'prodejny': prodejny,
        'default_prodejna_id': default_invoice_store_id(user, now=now),
        'domaci_prodejna_id': home,
        'aktualni_smena_prodejna_id': current,
    }


def user_can_access_polozka(user, polozka) -> bool:
    store_ids = accessible_store_ids(user)
    if store_ids is None:
        return True
    if not store_ids:
        return False
    return polozka.prodejna_id in store_ids


def require_finance_admin(request):
    """Vrátí Response 403 nebo None pokud je uživatel ADMIN."""
    if getattr(request.user, 'role', None) != 'ADMIN':
        return Response({'error': 'Nemáte oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    return None


def require_finance_invoice_access(request):
    """Admin, vedoucí nebo prodejce s domovskou prodejnou."""
    role = getattr(request.user, 'role', None)
    if role == 'ADMIN':
        return None
    if accessible_store_ids(request.user):
        return None
    return Response(
        {'error': 'Nemáte domácí prodejnu ani dnešní směnu, ke které jdou nahrát faktury.'},
        status=status.HTTP_403_FORBIDDEN,
    )


def finance_admin_view(view_func):
    """Dekorátor pro DRF @api_view – kontrola ADMIN před handlerem."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        denied = require_finance_admin(request)
        if denied:
            return denied
        return view_func(request, *args, **kwargs)
    return wrapper


def finance_invoice_view(view_func):
    """Admin nebo uživatel s přístupem k prodejně."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        denied = require_finance_invoice_access(request)
        if denied:
            return denied
        return view_func(request, *args, **kwargs)
    return wrapper
