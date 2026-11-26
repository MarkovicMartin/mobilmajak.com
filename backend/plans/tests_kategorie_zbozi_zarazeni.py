from django.test import SimpleTestCase

from plans.kategorie_zbozi_zarazeni import je_k_zapisu, nacti_katalog, rozhodni

KATALOG = [
    {'id': 15555, 'v': 's', 'n': 'iPhone 18 Pro Max'},
    {'id': 15554, 'v': 's', 'n': 'iPhone 18 Pro'},
    {'id': 14674, 'v': 's', 'n': 'Xiaomi Redmi 14C'},
    {'id': 15570, 'v': 's', 'n': 'Xiaomi Redmi 17'},
    {'id': 12609, 'v': 's', 'n': 'Galaxy A54'},
    {'id': 15565, 'v': 'p', 'n': 'Xiaomi Redmi 17'},
    {'id': 12604, 'v': 'p', 'n': 'Galaxy A54'},
    {'id': 15557, 'v': 'p', 'n': 'iPhone 18 Pro'},
    {'id': 15229, 'v': 'p', 'n': 'iPhone 17 Pro'},
    {'id': 15558, 'v': 'p', 'n': 'iPhone 18 Pro Max'},
    {'id': 15230, 'v': 'p', 'n': 'iPhone 17 Pro Max'},
    {'id': 13867, 'v': 'p', 'n': 'Xcover 7 / 7 Pro'},
    {'id': 9860, 'v': 'u', 'n': 'iPhone 12 / Mini / Pro / Pro Max'},
    {'id': 10416, 'v': 's', 'n': 'Galaxy A12'},
]


class RozhodniTests(SimpleTestCase):
    def test_sklo_bere_presnejsi_model(self):
        r = rozhodni(
            'Tvrzené / ochranné sklo Apple iPhone 18 Pro Max černé - 5D Mr. Monkey Glass',
            'P154391', KATALOG,
        )
        self.assertEqual(r['stav'], 'jiste')
        self.assertEqual([k['id'] for k in r['kategorie']], [15555])

    def test_kryt_se_dvema_modely(self):
        r = rozhodni(
            'DUX DUCIS case YIND compatible with MagSafe for iPhone 18 Pro / 17 Pro black',
            'P154785', KATALOG,
        )
        self.assertEqual(r['stav'], 'jiste')
        self.assertEqual({k['id'] for k in r['kategorie']}, {15557, 15229})

    def test_chybejici_druhy_model_zustava(self):
        r = rozhodni(
            'Tvrzené / ochranné sklo Xiaomi Redmi 14C / 17C černé',
            'P153734', KATALOG,
        )
        self.assertEqual(r['stav'], 'nejiste')
        self.assertEqual(r['duvod'], 'nepokryty_model')

    def test_kabel_a_taska_zůstávají(self):
        for nazev in (
            'EP-DG980BWE Samsung USB-C/USB-C Datový Kabel 3A 1m White',
            'Papírová taška 260x140x360mm, ploché ucho, 80gr',
            'Vodafone SIM karta Předplacenka 2GB',
            'Car charger Hoco USB A 93W black',
        ):
            r = rozhodni(nazev, 'P1', KATALOG)
            self.assertEqual(r['stav'], 'nejiste', nazev)

    def test_zapis_jen_sklo_a_kryt(self):
        sklo = rozhodni(
            'Tvrzené / ochranné sklo Apple iPhone 18 Pro Max černé - 5D Mr. Monkey Glass',
            'P154391', KATALOG,
        )
        telefon = rozhodni(
            'Apple iPhone 12 Mini 128GB modrý - použitý (C)',
            'V26110031', KATALOG,
        )
        kabel = rozhodni('EP-DG980BWE Samsung USB-C/USB-C Datový Kabel 3A 1m White', 'P1', KATALOG)
        self.assertTrue(je_k_zapisu(sklo))
        self.assertFalse(je_k_zapisu(telefon))
        self.assertFalse(je_k_zapisu(kabel))

    def test_pouzity_telefon_do_kose(self):
        r = rozhodni(
            'Apple iPhone 12 Mini 128GB modrý - použitý (C)',
            'V26110031', KATALOG,
        )
        self.assertEqual(r['stav'], 'jiste')
        self.assertEqual(r['kategorie'][0]['id'], 9860)

    def test_redmi_17_4g_a_5g_je_jeden_list(self):
        r = rozhodni(
            'Pouzdro / obal na Xiaomi Redmi 17 4G / 17 5G EU Luna Book Carbon blue',
            'P154585', KATALOG,
        )
        self.assertEqual(r['stav'], 'jiste')
        self.assertEqual([k['id'] for k in r['kategorie']], [15565])

    def test_xcover_bez_slova_galaxy(self):
        r = rozhodni('Smart Case Book for SAMSUNG Xcover 7 black', 'P128373', KATALOG)
        self.assertEqual(r['stav'], 'jiste')
        self.assertEqual(r['kategorie'][0]['id'], 13867)

    def test_sklo_kamery_neni_kryt(self):
        r = rozhodni(
            'OBAL:ME Ochrana Čoček pro Apple iPhone 18 Pro/18 Pro Max Light Blue',
            'P154266', KATALOG,
        )
        self.assertEqual(r['stav'], 'jiste')
        self.assertEqual({k['id'] for k in r['kategorie']}, {15554, 15555})

    def test_stejny_model_jine_znacky_se_neprida(self):
        katalog = KATALOG + [
            {'id': 9737, 'v': 'p', 'n': 'iPhone 13 Pro'},
            {'id': 13049, 'v': 'p', 'n': 'Xiaomi 13 Pro'},
            {'id': 15568, 'v': 'p', 'n': 'Xiaomi Redmi Note 17 Pro Max / Pro Plus'},
        ]
        iphone = rozhodni('Case for iPhone 13 Pro Easy Dual blue', 'P154231', katalog)
        self.assertEqual([k['id'] for k in iphone['kategorie']], [9737])
        redmi = rozhodni(
            'Case for Xiaomi Redmi Note 17 Pro Max 5G / 17 Pro Plus 5G Noble black',
            'P154643', katalog,
        )
        self.assertEqual(redmi['stav'], 'jiste')
        self.assertEqual([k['id'] for k in redmi['kategorie']], [15568])

    def test_katalog_ma_sklo_18_pro_max(self):
        katalog = nacti_katalog()
        nazvy = {(row['v'], row['n']) for row in katalog}
        self.assertIn(('s', 'iPhone 18 Pro Max'), nazvy)
        self.assertIn(('p', 'Xiaomi Redmi 17'), nazvy)
