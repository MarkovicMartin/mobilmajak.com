"""Nedostatky týdenního zakládání karet, které ve Sympliu není kam zapsat."""
from django.utils import timezone

from .models import ZakladaniNedostatek

TYPY = {kod for kod, _nazev in ZakladaniNedostatek.TYP_CHOICES}
TYP_LABEL = dict(ZakladaniNedostatek.TYP_CHOICES)


class NeplatnyNedostatek(ValueError):
    pass


def zapis_nedostatek(*, kod, typ, text, nazev='', zbozi_id=None):
    """Otevřený záznam stejného kódu a typu aktualizuje, jinak založí nový."""
    kod = (kod or '').strip()
    text = (text or '').strip()
    nazev = (nazev or '').strip()
    if not kod or not text:
        raise NeplatnyNedostatek('Chybí kód nebo text.')
    if typ not in TYPY:
        raise NeplatnyNedostatek('Neznámý typ.')
    if zbozi_id in ('', None):
        zbozi_id = None
    else:
        zbozi_id = int(zbozi_id)

    otevreny = (
        ZakladaniNedostatek.objects
        .filter(kod=kod, typ=typ, stav=ZakladaniNedostatek.STAV_OTEVRENO)
        .order_by('-vytvoreno')
        .first()
    )
    if otevreny:
        otevreny.text = text
        if nazev:
            otevreny.nazev = nazev
        if zbozi_id:
            otevreny.zbozi_id = zbozi_id
        otevreny.save(update_fields=['text', 'nazev', 'zbozi_id'])
        return otevreny, False

    row = ZakladaniNedostatek.objects.create(
        kod=kod,
        typ=typ,
        text=text,
        nazev=nazev,
        zbozi_id=zbozi_id,
    )
    return row, True


def oznac_vyreseno(pk, user):
    row = ZakladaniNedostatek.objects.filter(pk=pk).first()
    if not row:
        return None
    row.stav = ZakladaniNedostatek.STAV_VYRESENO
    row.vyreseno = timezone.now()
    row.vyresil = user
    row.save(update_fields=['stav', 'vyreseno', 'vyresil'])
    return row


def _jmeno(user):
    if not user:
        return ''
    jmeno = f'{(user.jmeno or "").strip()} {(user.prijmeni or "").strip()}'.strip()
    return jmeno or user.uzivatelske_jmeno


def na_radek(row):
    return {
        'id': row.id,
        'kod': row.kod,
        'zbozi_id': row.zbozi_id,
        'nazev': row.nazev,
        'typ': row.typ,
        'typ_label': TYP_LABEL.get(row.typ, row.typ),
        'text': row.text,
        'stav': row.stav,
        'vytvoreno': row.vytvoreno.isoformat() if row.vytvoreno else None,
        'vyreseno': row.vyreseno.isoformat() if row.vyreseno else None,
        'vyresil': _jmeno(row.vyresil),
    }


def radky(stav='otevreno'):
    qs = ZakladaniNedostatek.objects.select_related('vyresil')
    if stav != 'vse':
        qs = qs.filter(stav=stav)
    return [na_radek(row) for row in qs]
