"""Pomocné funkce pro směny – absence (dovolená, nemoc) bez prodejny."""

from __future__ import annotations

from django.db.models import Q

from stores.models import Prodejna

ABSENCE_SHIFT_TYPES = ('dovolena', 'nemoc')


def is_absence_shift(typ_smeny: str | None) -> bool:
    return typ_smeny in ABSENCE_SHIFT_TYPES


def resolve_prodejna(prodejna_input, typ_smeny: str):
    """Pro dovolenou/nemoc vrací None; jinak Prodejna nebo vyvolá výjimku."""
    if is_absence_shift(typ_smeny):
        return None
    if prodejna_input is None:
        raise ValueError('Chybí parametr prodejna')
    try:
        return Prodejna.objects.get(id=int(prodejna_input))
    except (ValueError, TypeError):
        prodejna_obj = Prodejna.objects.filter(
            Q(nazev__iexact=prodejna_input)
            | Q(nazev_kratkiy__iexact=prodejna_input)
            | Q(nazev_google_sheets__iexact=prodejna_input)
        ).first()
        if not prodejna_obj:
            raise Prodejna.DoesNotExist
        return prodejna_obj


def find_existing_shift(user, datum, prodejna_obj, typ_smeny: str):
    from .models import Smena

    if is_absence_shift(typ_smeny):
        return Smena.objects.filter(
            user=user,
            datum=datum,
            aktivni=True,
            typ_smeny__in=ABSENCE_SHIFT_TYPES,
        ).first()
    return Smena.objects.filter(
        user=user,
        datum=datum,
        prodejna=prodejna_obj,
        aktivni=True,
    ).first()


def apply_calendar_prodejna_filter(qs, prodejna):
    """Pracovní směny na pobočce + absence zaměstnanců s domovskou pobočkou."""
    if prodejna is None:
        return qs
    return qs.filter(
        Q(prodejna=prodejna)
        | Q(
            prodejna__isnull=True,
            typ_smeny__in=ABSENCE_SHIFT_TYPES,
            user__prodejna_id=prodejna.id,
        )
    )
