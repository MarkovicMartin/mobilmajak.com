from decimal import Decimal

from django.test import TestCase

from datetime import time

from analytics.dobropisy import (
    dobropis_polozka_q,
    dobropisy_totals,
    list_dobropisy,
    dobropisy_summary_by_prodejce,
)
from analytics.models import WebProdejeAll


class DobropisyTests(TestCase):
    def setUp(self):
        self.prodejce_a = 7001
        self.prodejce_b = 7002
        self.den = '2026-06-10'

    def _row(self, *, doklad, kod, cena, prodejce, nazev='Položka', kusy=1, den=None, cas=None):
        WebProdejeAll.objects.create(
            typ=den or self.den,
            doklad=doklad,
            kod=kod,
            nazev=nazev,
            pocet_kusu=kusy,
            cena_ks_vcl_dph=Decimal(str(cena)),
            id_prodejce=prodejce,
            stredisko='Test',
            cas_prodeje=cas,
        )

    def test_product_return_counts(self):
        self._row(doklad='DOB001', kod='P100', cena=-199, prodejce=self.prodejce_a)
        self._row(doklad='DOB002', kod='P200', cena=-299, prodejce=self.prodejce_a)
        self._row(doklad='UCT001', kod='SLEVA', cena=-50, prodejce=self.prodejce_a)
        WebProdejeAll.objects.create(
            typ=self.den,
            doklad='DOB003',
            kod='',
            nazev='Zaokrouhlení',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('-0.20'),
            id_prodejce=self.prodejce_b,
        )

        qs = WebProdejeAll.objects.filter(typ=self.den)
        totals = dobropisy_totals(qs)
        self.assertEqual(totals['polozky'], 2)
        self.assertEqual(totals['doklady'], 2)
        self.assertAlmostEqual(totals['castka'], -498.0)

        summary = dobropisy_summary_by_prodejce(qs, users_map={self.prodejce_a: 'Anna'})
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['prodejce'], 'Anna')
        self.assertEqual(summary[0]['polozky'], 2)

        rows = list_dobropisy(qs, users_map={self.prodejce_a: 'Anna'})
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['castka'] < 0 for r in rows))

    def test_dobropis_polozka_q_excludes_body(self):
        self._row(doklad='UCT002', kod='BODY', cena=-10, prodejce=self.prodejce_a)
        qs = WebProdejeAll.objects.filter(typ=self.den)
        self.assertEqual(qs.filter(dobropis_polozka_q()).count(), 0)

    def test_mirror_pairing_same_day(self):
        self._row(
            doklad='UCT100', kod='P100', cena=199, prodejce=self.prodejce_a,
            cas=time(10, 0, 0),
        )
        self._row(
            doklad='DOB100', kod='P100', cena=-199, prodejce=self.prodejce_a,
            cas=time(10, 15, 0),
        )
        qs = WebProdejeAll.objects.filter(typ=self.den)
        rows = list_dobropisy(qs, users_map={self.prodejce_a: 'Anna'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['pairing'], 'zrcadlo')
        self.assertEqual(rows[0]['puvodni_doklad'], 'UCT100')

    def test_pairing_without_match(self):
        self._row(doklad='DOB200', kod='P999', cena=-100, prodejce=self.prodejce_a)
        qs = WebProdejeAll.objects.filter(typ=self.den)
        rows = list_dobropisy(qs)
        self.assertEqual(rows[0]['pairing'], 'bez_paru')
        self.assertIsNone(rows[0]['puvodni_doklad'])

    def test_pairing_other_day(self):
        self._row(doklad='UCT300', kod='P300', cena=300, prodejce=self.prodejce_a, den='2026-06-09')
        self._row(doklad='DOB300', kod='P300', cena=-300, prodejce=self.prodejce_a)
        qs = WebProdejeAll.objects.filter(typ=self.den)
        rows = list_dobropisy(qs, search_qs=WebProdejeAll.objects.all())
        self.assertEqual(rows[0]['pairing'], 'par')
        self.assertEqual(rows[0]['puvodni_doklad'], 'UCT300')
