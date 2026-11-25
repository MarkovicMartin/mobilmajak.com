"""Problémy sobotního zpracování karet z kategorie 201, !Import / PARTNER PL."""
import re

from django.utils import timezone

from .models import AutomatizaceKaretProblem, ZakladaniNedostatek

ZDROJOVA_KATEGORIE = 201
DODAVATEL_PODLE_SLOZKY = {
    201: {'id': 2, 'nazev': 'PARTNER PL'},
}
TYPY = {kod for kod, _nazev in ZakladaniNedostatek.TYP_CHOICES}
TYP_LABEL = dict(ZakladaniNedostatek.TYP_CHOICES)


class NeplatnyProblem(ValueError):
    pass


def zapis_problem(*, kod, typ, text, nazev='', zbozi_id=None):
    """Otevřený záznam stejného kódu a typu aktualizuje, jinak založí nový."""
    kod = (kod or '').strip()
    text = (text or '').strip()
    nazev = (nazev or '').strip()
    if not kod or not text:
        raise NeplatnyProblem('Chybí kód nebo text.')
    if typ not in TYPY:
        raise NeplatnyProblem('Neznámý typ.')
    if zbozi_id in ('', None):
        zbozi_id = None
    else:
        zbozi_id = int(zbozi_id)

    otevreny = (
        AutomatizaceKaretProblem.objects
        .filter(kod=kod, typ=typ, stav=AutomatizaceKaretProblem.STAV_OTEVRENO)
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

    row = AutomatizaceKaretProblem.objects.create(
        kod=kod,
        typ=typ,
        text=text,
        nazev=nazev,
        zbozi_id=zbozi_id,
    )
    return row, True


def oznac_vyreseno(pk, user):
    row = AutomatizaceKaretProblem.objects.filter(pk=pk).first()
    if not row:
        return None
    row.stav = AutomatizaceKaretProblem.STAV_VYRESENO
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
    qs = AutomatizaceKaretProblem.objects.select_related('vyresil')
    if stav != 'vse':
        qs = qs.filter(stav=stav)
    return [na_radek(row) for row in qs]


def dodavatel_slozky(kategorie_id):
    """Dodavatel patří jen ke složce, která je ve zpracování. Ostatní složky nic nedostanou."""
    try:
        return DODAVATEL_PODLE_SLOZKY.get(int(kategorie_id))
    except (TypeError, ValueError):
        return None


def doplnit_dodavatele(aktualni_id, kategorie_id=ZDROJOVA_KATEGORIE):
    """Vrátí PARTNER PL, když je pole Dodavatel prázdné. Vyplněného jiného dodavatele nechá."""
    cil = dodavatel_slozky(kategorie_id)
    if not cil:
        return None
    if aktualni_id in (None, '', 0, '0', 'none'):
        return cil
    return None


def je_skladem(text):
    """Skladem je jen kladný počet kusů. Neznámý text skladem není."""
    t = (text or '').replace('\xa0', ' ').lower()
    if not t or 'není' in t or 'neni' in t:
        return False
    match = re.search(r'(\d+)', t)
    return bool(match) and int(match.group(1)) > 0


def problemy_mereni(mereni):
    """Konkrétní mezery karty skladem. Mimo sklad a nejasný sklad se nezapisují."""
    if not je_skladem(mereni.get('sklad')):
        return []
    kod = (mereni.get('kod') or '').strip()
    if not kod:
        return []
    nalez = []
    if int(mereni.get('fotek') or 0) <= 0:
        nalez.append({
            'typ': 'chybejici_fotka',
            'text': 'Karta v !Import / PARTNER PL je skladem a nemá vlastní fotku.',
        })
    if mereni.get('ceny_prazdne'):
        nalez.append({
            'typ': 'nezname_ceny',
            'text': 'Karta je skladem a nemá vyplněnou pokladní ani e-shopovou cenu.',
        })
    if mereni.get('popis_prazdny'):
        nalez.append({
            'typ': 'jine',
            'text': 'Karta je skladem a nemá popis. Automat popis od dodavatele sám nedoplňuje.',
        })
    return nalez
