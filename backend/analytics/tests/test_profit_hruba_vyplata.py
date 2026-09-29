"""Výnos pro firmu odečítá hrubou výplatu (HPP + DPP), ne jen body."""
from django.test import SimpleTestCase

from analytics.profit_by_salesperson import hruba_vyplata_z_radku
from shifts.hpp_dpp import attach_hpp_dpp_to_row


class HrubaVyplataZRadkuTest(SimpleTestCase):
    def test_hruba_zahrnuje_odvody(self):
        row = attach_hpp_dpp_to_row({
            'celkem_body': 25000,
            'odpracovano_h': 168,
            'is_brigadnik': False,
        })
        hruba = hruba_vyplata_z_radku(row)
        split = row['hpp_dpp']
        self.assertEqual(hruba, split['hpp_hruba'] + split['dpp_hruba'])
        self.assertGreater(hruba, row['celkem_body'])

    def test_brigadnik_zostava_na_bodech(self):
        self.assertEqual(
            hruba_vyplata_z_radku({'celkem_body': 8000, 'hpp_dpp': None}),
            8000.0,
        )
