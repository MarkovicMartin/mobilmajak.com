"""Synchronizace vedoucího prodejny ↔ mzda_doplnky vedouci_pobocky."""
from decimal import Decimal

from django.db import transaction

from users.models import WebUser
from users.mzda_utils import normalize_mzda_doplnky

from .models import Prodejna

VEDOUCI_POBOCKY_KOD = 'vedouci_pobocky'
VEDOUCI_POBOCKY_NAZEV = 'Odměna vedoucí pobočky'
VEDOUCI_POBOCKY_VYCHOZI_BODY = Decimal('2000')


def _remove_vedouci_doplnek(user):
    doplnky = normalize_mzda_doplnky(getattr(user, 'mzda_doplnky', None))
    filtered = [d for d in doplnky if d.get('kod') != VEDOUCI_POBOCKY_KOD]
    user.mzda_doplnky = filtered
    user.save(update_fields=['mzda_doplnky'])


def _add_vedouci_doplnek(user, castka=None):
    castka_val = float(castka if castka is not None else VEDOUCI_POBOCKY_VYCHOZI_BODY)
    doplnky = normalize_mzda_doplnky(getattr(user, 'mzda_doplnky', None))
    doplnky = [d for d in doplnky if d.get('kod') != VEDOUCI_POBOCKY_KOD]
    doplnky.append({
        'kod': VEDOUCI_POBOCKY_KOD,
        'nazev': VEDOUCI_POBOCKY_NAZEV,
        'castka': castka_val,
    })
    user.mzda_doplnky = doplnky
    user.save(update_fields=['mzda_doplnky'])


@transaction.atomic
def assign_vedouci_prodejny(prodejna_id, user_id, castka=None):
    """Nastaví vedoucího prodejny. Jeden vedoucí na pobočku, uživatel max. jedna pobočka."""
    prodejna = Prodejna.objects.get(pk=prodejna_id)
    old_user_id = prodejna.vedouci_user_id

    if user_id in (None, '', 0, '0'):
        if old_user_id:
            try:
                old_user = WebUser.objects.get(pk=old_user_id)
                _remove_vedouci_doplnek(old_user)
            except WebUser.DoesNotExist:
                pass
        prodejna.vedouci_user_id = None
        prodejna.save(update_fields=['vedouci_user_id'])
        return prodejna

    user_id = int(user_id)
    new_user = WebUser.objects.get(pk=user_id)

    if old_user_id and old_user_id != user_id:
        try:
            old_user = WebUser.objects.get(pk=old_user_id)
            _remove_vedouci_doplnek(old_user)
        except WebUser.DoesNotExist:
            pass

    other_stores = Prodejna.objects.filter(vedouci_user_id=user_id).exclude(pk=prodejna_id)
    for other in other_stores:
        other.vedouci_user_id = None
        other.save(update_fields=['vedouci_user_id'])

    prodejna.vedouci_user_id = user_id
    prodejna.save(update_fields=['vedouci_user_id'])
    _add_vedouci_doplnek(new_user, castka=castka)
    return prodejna


@transaction.atomic
def sync_vedouci_from_user(user_id, vedouci_prodejna_id):
    """Uživatel jako vedoucí vybrané prodejny (z UserManagement)."""
    if not vedouci_prodejna_id:
        stores = Prodejna.objects.filter(vedouci_user_id=user_id)
        for s in stores:
            assign_vedouci_prodejny(s.id, None)
        return
    assign_vedouci_prodejny(int(vedouci_prodejna_id), int(user_id))
