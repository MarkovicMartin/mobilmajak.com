"""Testy mapování kategorií a servisního plnění."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from plans.category_mapping import (
    PRACOVNI_KATEGORIE,
    kategorie_case_sql,
    is_pracovni_kategorie,
    normalize_plan_kategorie_kod,
    plan_skryt_ostatni,
    seller_kategorie_nazev,
)
from plans.servis_plneni import apply_servis_to_plneni_dict


class KategorieCaseSqlTests(SimpleTestCase):
    def test_pracovni_kategorie_ve_fallbacku(self):
        sql = kategorie_case_sql()
        for kat in PRACOVNI_KATEGORIE:
            self.assertIn(kat, sql)

    def test_sluzby_pred_servisem(self):
        sql = kategorie_case_sql()
        self.assertLess(sql.index('SLUZBY'), sql.index('SERVIS'))

    def test_else_je_zbytek(self):
        sql = kategorie_case_sql()
        self.assertIn("ELSE 'PRISLUSENSTVI_OSTATNI'", sql)

    def test_is_pracovni(self):
        self.assertTrue(is_pracovni_kategorie('Nově naskladněno'))
        self.assertFalse(is_pracovni_kategorie('PŘÍSLUŠENSTVÍ'))


class SellerLabelsTests(SimpleTestCase):
    def test_zbytek_label(self):
        self.assertEqual(seller_kategorie_nazev('PRISLUSENSTVI_OSTATNI'), 'Zbytek')

    def test_ostatni_slouceni_od_cervna_2026(self):
        self.assertTrue(plan_skryt_ostatni(2026, 6))
        self.assertFalse(plan_skryt_ostatni(2026, 5))
        self.assertEqual(
            normalize_plan_kategorie_kod('OSTATNI', 2026, 6),
            'PRISLUSENSTVI_OSTATNI',
        )
        self.assertEqual(normalize_plan_kategorie_kod('OSTATNI', 2026, 5), 'OSTATNI')


class ServisPlneniMergeTests(SimpleTestCase):
    @patch('plans.servis_plneni.servis_plneni_kusy_for_user')
    def test_nahradí_servis_z_prodejce(self, mock_servis):
        mock_servis.return_value = 7
        out = apply_servis_to_plneni_dict({'SERVIS': 99, 'SLUZBY': 3}, 1, '2026-01-01', '2026-02-01')
        self.assertEqual(out['SERVIS'], 7)
        self.assertEqual(out['SLUZBY'], 3)

    @patch('plans.servis_plneni.servis_plneni_kusy_for_user')
    def test_odstraní_servis_když_nula(self, mock_servis):
        mock_servis.return_value = 0
        out = apply_servis_to_plneni_dict({'SERVIS': 5}, 1, '2026-01-01', '2026-02-01')
        self.assertNotIn('SERVIS', out)
