"""Testy sloučení kategorií nákladů."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.kategorie_slouceni import sloucit_kategorie
from finance.kategorizace import apply_builtin_rules
from finance.models import FioKategorizacniPravidlo, NakladKategorie, NakladPolozka


def _kat(nazev, **defaults):
    obj, _ = NakladKategorie.objects.get_or_create(nazev=nazev, defaults=defaults)
    return obj


class KategorieSlouceniTests(TestCase):
    def setUp(self):
        mzdy = _kat('Mzdy', poradi=100, typ_dph='bez')
        zam = _kat('Mzdy – zaměstnanci', poradi=101, typ_dph='bez', parent=mzdy)
        soc = _kat('Odvody – sociální', poradi=111, typ_dph='bez')
        najem_gl = _kat('Nájem – Globus (GL)', poradi=301, typ_dph='z_faktury')
        _kat('Nájmy', poradi=300, typ_dph='z_faktury')
        energie_el = _kat('Energie – elektřina', poradi=401, typ_dph='z_faktury')
        _kat('Energie', poradi=400, typ_dph='z_faktury')
        hosting = _kat('IT – hosting / domény', poradi=503, typ_dph='z_faktury')
        _kat('IT a e-shop', poradi=500, typ_dph='z_faktury')
        zasilkovna = _kat('Doprava – Zásilkovna / kurýr', poradi=601, typ_dph='z_faktury')
        _kat('Doprava', poradi=600, typ_dph='z_faktury')
        spotreba_uklid = _kat('Spotřeba – úklid', poradi=801, typ_dph='z_faktury')
        _kat('Spotřeba prodejny', poradi=800, typ_dph='z_faktury')
        parent = _kat('Zboží / sklad', poradi=900, typ_dph='z_faktury')
        nakup = _kat('Zboží – nákup sklad', poradi=901, typ_dph='z_faktury', parent=parent)
        vykup = _kat('Výkup', poradi=903, typ_dph='bez', parent=parent)

        self._polozka(zam, 'mzda')
        self._polozka(soc, 'odvod')
        self._polozka(najem_gl, 'najem')
        self._polozka(energie_el, 'energie')
        self._polozka(hosting, 'hosting')
        self._polozka(zasilkovna, 'doprava')
        self._polozka(spotreba_uklid, 'spotreba')
        self._polozka(nakup, 'nakup')
        self._polozka(vykup, 'vykup')
        FioKategorizacniPravidlo.objects.create(
            zprava_obsahuje='cssz', kategorie=soc, aktivni=True,
        )

    def _polozka(self, kat, suffix):
        return NakladPolozka.objects.create(
            datum=date(2026, 8, 1),
            rok=2026,
            mesic=8,
            castka=Decimal('-10'),
            kategorie=kat,
            zdroj=NakladPolozka.ZDROJ_FIO,
            fio_id=f'fio:merge-{suffix}',
        )

    def test_merge_moves_items_and_deactivates_sources(self):
        sloucit_kategorie(NakladKategorie, NakladPolozka, FioKategorizacniPravidlo)
        mzdy = NakladKategorie.objects.get(nazev='Mzdy')
        self.assertTrue(mzdy.aktivni)
        self.assertEqual(
            NakladPolozka.objects.filter(fio_id='fio:merge-mzda').get().kategorie_id,
            mzdy.id,
        )
        self.assertEqual(
            NakladPolozka.objects.filter(fio_id='fio:merge-odvod').get().kategorie_id,
            mzdy.id,
        )
        self.assertFalse(NakladKategorie.objects.get(nazev='Mzdy – zaměstnanci').aktivni)
        self.assertFalse(NakladKategorie.objects.get(nazev='Odvody – sociální').aktivni)

        najmy = NakladKategorie.objects.get(nazev='Nájmy')
        self.assertEqual(
            NakladPolozka.objects.get(fio_id='fio:merge-najem').kategorie_id,
            najmy.id,
        )
        energie = NakladKategorie.objects.get(nazev='Energie')
        self.assertEqual(
            NakladPolozka.objects.get(fio_id='fio:merge-energie').kategorie_id,
            energie.id,
        )
        self.assertFalse(NakladKategorie.objects.get(nazev='Energie – elektřina').aktivni)
        it = NakladKategorie.objects.get(nazev='IT a e-shop')
        self.assertEqual(
            NakladPolozka.objects.get(fio_id='fio:merge-hosting').kategorie_id,
            it.id,
        )
        doprava = NakladKategorie.objects.get(nazev='Doprava')
        self.assertEqual(
            NakladPolozka.objects.get(fio_id='fio:merge-doprava').kategorie_id,
            doprava.id,
        )
        spotreba = NakladKategorie.objects.get(nazev='Spotřeba prodejny')
        self.assertEqual(
            NakladPolozka.objects.get(fio_id='fio:merge-spotreba').kategorie_id,
            spotreba.id,
        )
        self.assertFalse(NakladKategorie.objects.get(nazev='Spotřeba – úklid').aktivni)
        zbozi = NakladKategorie.objects.get(nazev='Nákup zboží / výkup')
        self.assertEqual(
            NakladPolozka.objects.get(fio_id='fio:merge-nakup').kategorie_id,
            zbozi.id,
        )
        self.assertEqual(
            NakladPolozka.objects.get(fio_id='fio:merge-vykup').kategorie_id,
            zbozi.id,
        )
        self.assertEqual(
            FioKategorizacniPravidlo.objects.get(zprava_obsahuje='cssz').kategorie_id,
            mzdy.id,
        )


class KategorizaceSlouceneNazvyTests(TestCase):
    def setUp(self):
        _kat('Mzdy', poradi=100, typ_dph='bez')
        _kat('Nájmy', poradi=300, typ_dph='z_faktury')
        _kat('IT a e-shop', poradi=500, typ_dph='z_faktury')

    def test_odvody_do_mezd(self):
        r = apply_builtin_rules({'popis': '', 'zprava': 'OSSZ pojistne'}, zdroj=NakladPolozka.ZDROJ_FIO)
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Mzdy').id)

    def test_najem_jedna_kategorie(self):
        r = apply_builtin_rules({'popis': '', 'zprava': 'najem globus'})
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='Nájmy').id)
        self.assertEqual(r.prodejna_id, 1)

    def test_hosting_do_it(self):
        r = apply_builtin_rules({'popis': '', 'zprava': 'Webglobe hosting'}, zdroj=NakladPolozka.ZDROJ_FIO)
        self.assertEqual(r.kategorie_id, NakladKategorie.objects.get(nazev='IT a e-shop').id)
