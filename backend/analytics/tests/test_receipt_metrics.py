"""Testy metrik účtenek (varianta 1)."""
from decimal import Decimal
from django.test import TestCase

from analytics.models import WebProdejeAll
from analytics.receipt_metrics import (
    count_active_receipts,
    prumer_hodnota_uctenky,
    prumer_polozek_uctu,
    qualifying_polozka_q,
    sum_obrat_s_dph,
)


class ReceiptMetricsTestCase(TestCase):
    """Scénáře prodej + dobropis bez druhého dokladu v jmenovateli."""

    def setUp(self):
        self.prodejce_id = 9001
        self.den = '2026-05-22'

    def _row(self, doklad, kod, cena, kusy=1, nazev='Položka'):
        WebProdejeAll.objects.create(
            typ=self.den,
            doklad=doklad,
            kod=kod,
            nazev=nazev,
            pocet_kusu=kusy,
            cena_ks_vcl_dph=Decimal(str(cena)),
            id_prodejce=self.prodejce_id,
            stredisko='Test',
        )

    def test_prodej_plus_dobropis_varianta_1(self):
        """1 prodej + plný dobropis → 1 aktivní účtenka, průměr pol. 1.0, AOV ~0."""
        self._row('UCT001', 'P100', 199)
        self._row('DOB001', 'P100', -199, nazev='Dobropis')

        qs = WebProdejeAll.objects.filter(id_prodejce=self.prodejce_id, typ=self.den)
        polozky_nad_29 = qs.filter(qualifying_polozka_q()).count()
        doklady = count_active_receipts(qs)
        obrat = float(sum_obrat_s_dph(qs))

        self.assertEqual(polozky_nad_29, 1)
        self.assertEqual(doklady, 1)
        self.assertEqual(prumer_polozek_uctu(polozky_nad_29, doklady), 1.0)
        self.assertAlmostEqual(obrat, 0.0, places=2)
        self.assertEqual(prumer_hodnota_uctenky(obrat, doklady), 0.0)

    def test_prodej_dobropis_novy_prodej(self):
        """Prodej A + dobropis A + prodej B → 2 aktivní účtenky, průměr pol. 1.0."""
        self._row('UCT_A', 'P100', 199)
        self._row('DOB_A', 'P100', -199)
        self._row('UCT_B', 'P200', 299)

        qs = WebProdejeAll.objects.filter(id_prodejce=self.prodejce_id, typ=self.den)
        polozky_nad_29 = qs.filter(qualifying_polozka_q()).count()
        doklady = count_active_receipts(qs)
        obrat = float(sum_obrat_s_dph(qs))

        self.assertEqual(polozky_nad_29, 2)
        self.assertEqual(doklady, 2)
        self.assertEqual(prumer_polozek_uctu(polozky_nad_29, doklady), 1.0)
        self.assertAlmostEqual(obrat, 299.0, places=2)
        self.assertEqual(prumer_hodnota_uctenky(obrat, doklady), 149.5)

    def test_doprava_bez_kodu_nezvysuje_doklady(self):
        """Řádek bez kódu (doprava) nepočítá aktivní účtenku."""
        self._row('UCT001', 'P100', 199)
        WebProdejeAll.objects.create(
            typ=self.den,
            doklad='UCT002',
            kod='',
            nazev='Doprava',
            pocet_kusu=1,
            cena_ks_vcl_dph=Decimal('50'),
            id_prodejce=self.prodejce_id,
        )

        qs = WebProdejeAll.objects.filter(id_prodejce=self.prodejce_id, typ=self.den)
        self.assertEqual(count_active_receipts(qs), 1)
