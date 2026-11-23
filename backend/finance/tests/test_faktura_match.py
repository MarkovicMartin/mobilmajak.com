"""Testy porovnání faktury s pokladnou."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from unittest.mock import patch

from finance.faktura_match import match_doklad_to_polozka
from finance.faktura_process import maybe_auto_schvalit_pokladnu
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

    def _uloz_shodu(self, doklad, polozka):
        match = match_doklad_to_polozka(doklad, polozka)
        doklad.match_stav = match['stav']
        doklad.match_detail = match
        doklad.save(update_fields=['match_stav', 'match_detail'])

    @patch('finance.flexi_sync.is_flexi_sync_enabled', return_value=False)
    def test_pokladna_se_shodou_schvali_sama(self, _flexi):
        self._uloz_shodu(self.doklad, self.polozka)
        doklad = maybe_auto_schvalit_pokladnu(self.doklad)
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_SCHVALENO)
        self.assertIsNone(doklad.schvalil_user_id)
        self.assertTrue((doklad.match_detail or {}).get('auto_schvaleno'))

    @patch('finance.flexi_sync.is_flexi_sync_enabled', return_value=False)
    def test_ucet_ceka_na_schvaleni(self, _flexi):
        self.polozka.zdroj = NakladPolozka.ZDROJ_FIO
        self.polozka.save(update_fields=['zdroj'])
        self.doklad.match_stav = FinanceDoklad.MATCH_OK
        self.doklad.match_detail = {
            'stav': FinanceDoklad.MATCH_OK,
            'checks': [
                {'pole': 'dodavatel', 'stav': FinanceDoklad.MATCH_OK},
                {'pole': 'castka_celkem', 'stav': FinanceDoklad.MATCH_OK},
            ],
        }
        self.doklad.save(update_fields=['match_stav', 'match_detail'])
        doklad = maybe_auto_schvalit_pokladnu(self.doklad)
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_KE_KONTROLE)

    @patch('finance.flexi_sync.is_flexi_sync_enabled', return_value=False)
    def test_pokladna_bez_castky_zustava_ke_kontrole(self, _flexi):
        self.doklad.castka_celkem = Decimal('999')
        self.doklad.save(update_fields=['castka_celkem'])
        self._uloz_shodu(self.doklad, self.polozka)
        doklad = maybe_auto_schvalit_pokladnu(self.doklad)
        self.assertEqual(doklad.stav, FinanceDoklad.STAV_KE_KONTROLE)
