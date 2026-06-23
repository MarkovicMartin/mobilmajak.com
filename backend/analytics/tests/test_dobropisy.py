from decimal import Decimal

from django.test import TestCase

from datetime import time

from analytics.dobropisy import (
    ORIGINAL_SALE_LOOKBACK_DAYS,
    build_pairing_search_qs,
    dobropis_polozka_q,
    dobropisy_totals,
    list_dobropisy,
    dobropisy_summary_by_prodejce,
)
from analytics.models import DobropisPairingCache, WebProdejeAll


class DobropisyTests(TestCase):
    def setUp(self):
        self.prodejce_a = 7001
        self.prodejce_b = 7002
        self.den = '2026-06-10'

    def _row(self, *, doklad, kod, cena, prodejce, nazev='Položka', kusy=1, den=None, cas=None, stredisko='Test'):
        WebProdejeAll.objects.create(
            typ=den or self.den,
            doklad=doklad,
            kod=kod,
            nazev=nazev,
            pocet_kusu=kusy,
            cena_ks_vcl_dph=Decimal(str(cena)),
            id_prodejce=prodejce,
            stredisko=stredisko,
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
        self.assertEqual(rows[0]['bez_paru_duvod'], 'kod_nenalezen')

    def test_bez_paru_hint_jiny_prodejce(self):
        self._row(doklad='UCT400', kod='P400', cena=400, prodejce=self.prodejce_a)
        self._row(doklad='DOB400', kod='P400', cena=-400, prodejce=self.prodejce_b)
        qs = WebProdejeAll.objects.filter(typ=self.den)
        rows = list_dobropisy(qs, search_qs=WebProdejeAll.objects.all())
        dob = next(r for r in rows if r['doklad'] == 'DOB400')
        self.assertEqual(dob['pairing'], 'bez_paru')
        self.assertEqual(dob['bez_paru_duvod'], 'jiny_prodejce')
        self.assertEqual(dob['kandidat_doklad'], 'UCT400')

    def test_bez_paru_hint_mimo_okno(self):
        self._row(doklad='UCT500', kod='P500', cena=500, prodejce=self.prodejce_a, den='2026-05-01')
        self._row(doklad='DOB500', kod='P500', cena=-500, prodejce=self.prodejce_a)
        qs = WebProdejeAll.objects.filter(typ=self.den)
        rows = list_dobropisy(qs, search_qs=WebProdejeAll.objects.all())
        self.assertEqual(rows[0]['bez_paru_duvod'], 'mimo_okno')
        self.assertEqual(rows[0]['kandidat_doklad'], 'UCT500')

    def test_pairing_other_day(self):
        self._row(doklad='UCT300', kod='P300', cena=300, prodejce=self.prodejce_a, den='2026-06-09')
        self._row(doklad='DOB300', kod='P300', cena=-300, prodejce=self.prodejce_a)
        qs = WebProdejeAll.objects.filter(typ=self.den)
        rows = list_dobropisy(qs, search_qs=WebProdejeAll.objects.all())
        self.assertEqual(rows[0]['pairing'], 'par')
        self.assertEqual(rows[0]['puvodni_doklad'], 'UCT300')

    def test_pairing_search_qs_scoped_to_dobropis_stores(self):
        from datetime import date

        self._row(
            doklad='DOB-Z', kod='PZ', cena=-50, prodejce=self.prodejce_a, stredisko='Zlín',
        )
        WebProdejeAll.objects.create(
            typ=self.den,
            doklad='UCT-G',
            kod='PG',
            nazev='Globus prodej',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('100'),
            id_prodejce=self.prodejce_a,
            stredisko='Globus',
        )
        month_qs = WebProdejeAll.objects.filter(typ=self.den)
        search = build_pairing_search_qs(
            month_qs,
            month_start=date(2026, 6, 1),
            month_end=date(2026, 6, 30),
        )
        strediska = set(search.values_list('stredisko', flat=True))
        self.assertEqual(strediska, {'Zlín'})

        search_zlin = build_pairing_search_qs(
            month_qs,
            month_start=date(2026, 6, 1),
            month_end=date(2026, 6, 30),
            prodejna='Zlín',
        )
        self.assertEqual(
            set(search_zlin.values_list('stredisko', flat=True)),
            {'Zlín'},
        )

    def test_lookback_is_30_days(self):
        self.assertEqual(ORIGINAL_SALE_LOOKBACK_DAYS, 30)

    def test_pairing_persisted_in_cache(self):
        self._row(
            doklad='UCT100', kod='P100', cena=199, prodejce=self.prodejce_a,
            cas=time(10, 0, 0),
        )
        self._row(
            doklad='DOB100', kod='P100', cena=-199, prodejce=self.prodejce_a,
            cas=time(10, 15, 0),
        )
        qs = WebProdejeAll.objects.filter(typ=self.den)
        list_dobropisy(qs, users_map={self.prodejce_a: 'Anna'})
        self.assertEqual(DobropisPairingCache.objects.filter(pairing='zrcadlo').count(), 1)
        rows2 = list_dobropisy(qs, users_map={self.prodejce_a: 'Anna'})
        self.assertEqual(rows2[0]['pairing'], 'zrcadlo')
        self.assertEqual(DobropisPairingCache.objects.count(), 1)
