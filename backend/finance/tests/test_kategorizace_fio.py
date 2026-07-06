"""Testy Fio pravidel kategorizace."""
from django.test import TestCase

from finance.kategorizace import apply_builtin_rules
from finance.models import NakladKategorie, NakladPolozka


class FioKategorizaceTests(TestCase):
    def setUp(self):
        NakladKategorie.objects.get_or_create(
            nazev='Mzdy', defaults={'poradi': 100, 'typ_dph': 'bez'},
        )
        NakladKategorie.objects.get_or_create(
            nazev='Mzdy – zaměstnanci',
            defaults={'poradi': 101, 'typ_dph': 'bez', 'parent_id': None},
        )
        NakladKategorie.objects.get_or_create(
            nazev='Reklama – firma / online', defaults={'poradi': 207, 'typ_dph': 'z_faktury'},
        )
        NakladKategorie.objects.get_or_create(
            nazev='IT – hosting / domény', defaults={'poradi': 503, 'typ_dph': 'z_faktury'},
        )
        NakladKategorie.objects.get_or_create(
            nazev='Účetnictví a právní', defaults={'poradi': 950, 'typ_dph': 'z_faktury'},
        )
        parent, _ = NakladKategorie.objects.get_or_create(
            nazev='Zboží / sklad', defaults={'poradi': 900, 'typ_dph': 'z_faktury'},
        )
        NakladKategorie.objects.get_or_create(
            nazev='Zboží – nákup sklad',
            defaults={'poradi': 901, 'typ_dph': 'z_faktury', 'parent': parent},
        )

    def _fio(self, zprava):
        return apply_builtin_rules(
            {'popis': '', 'zprava': zprava},
            zdroj=NakladPolozka.ZDROJ_FIO,
        )

    def test_dpp(self):
        r = self._fio('DPP 68 - Monika Krizkova - Dobirka')
        self.assertEqual(r.pravidlo, 'fio:mzdy_vyplata')

    def test_facebook(self):
        r = self._fio('Nákup: FACEBK *YD8FGQHBT2, FACEBOOK.COM')
        self.assertEqual(r.pravidlo, 'fio:facebook')

    def test_aswo(self):
        r = self._fio('ASWO Czech s.r.o. - zbozi')
        self.assertEqual(r.pravidlo, 'fio:aswo')

    def test_moneylive(self):
        r = self._fio('Moneylive s.r.o. - ucetni uzaverka')
        self.assertEqual(r.pravidlo, 'fio:ucetnictvi')
