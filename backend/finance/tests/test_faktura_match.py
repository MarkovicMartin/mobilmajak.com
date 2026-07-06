"""Testy porovnání faktury s pokladnou."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.faktura_match import match_doklad_to_polozka
from finance.models import FinanceDoklad, NakladPolozka


class FakturaMatchTests(TestCase):
    def setUp(self):
        self.polozka = NakladPolozka.objects.create(
            datum=date(2026, 6, 10),
            rok=2026,
            mesic=6,
            castka=Decimal('-500'),
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA,
            prodejna_id=6,
            popis='Manuální výdej PANFICO - servis 202601234',
            fio_id='symplio:6:test',
        )
        self.doklad = FinanceDoklad.objects.create(
            dodavatel_nazev='PANFICO s.r.o.',
            cislo_faktury='202601234',
            castka_celkem=Decimal('500'),
            stav=FinanceDoklad.STAV_KE_KONTROLE,
            naklad_polozka=self.polozka,
        )

    def test_match_ok(self):
        m = match_doklad_to_polozka(self.doklad, self.polozka)
        self.assertEqual(m['stav'], FinanceDoklad.MATCH_OK)

    def test_match_fail_castka(self):
        self.doklad.castka_celkem = Decimal('999')
        m = match_doklad_to_polozka(self.doklad, self.polozka)
        self.assertEqual(m['stav'], FinanceDoklad.MATCH_FAIL)
