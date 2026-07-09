from django.test import TestCase

from stores.models import Prodejna
from shifts.views import _normalize_pozice_smeny


class SkoleniPositionTest(TestCase):
    def setUp(self):
        self.senimo = Prodejna.objects.create(
            nazev='Senimo',
            nazev_kratkiy='SEN',
            aktivni=True,
        )
        self.globus = Prodejna.objects.create(
            nazev='Globus',
            nazev_kratkiy='GLO',
            aktivni=True,
        )

    def test_skoleni_povoleno_na_senimo(self):
        pozice = _normalize_pozice_smeny(self.senimo, 'prace', 'skoleni')
        self.assertEqual(pozice, 'skoleni')

    def test_skoleni_jinde_fallback_prodej(self):
        pozice = _normalize_pozice_smeny(self.globus, 'prace', 'skoleni')
        self.assertEqual(pozice, 'prodej')
