import random
from calendar import monthrange
from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from shifts.models import Smena, VyjezdNavrh, VyjezdNotifikace
from shifts.vyjezd import dopln_vyjezdy, due_months, store_key
from stores.models import Prodejna
from stores.oteviraci_doba_utils import DNY_KLICE, default_oteviraci_doba
from users.models import WebUser


def _hours(open_weekdays):
    cfg = default_oteviraci_doba()
    cfg['stejne_pro_vsechny'] = False
    for index, key in enumerate(DNY_KLICE):
        if index in open_weekdays:
            cfg['dny'][key] = {'od': '09:00', 'do': '18:00'}
        else:
            cfg['dny'][key] = {'zavreno': True}
    return cfg


def _closed():
    return _hours(set())


class VyjezdNavrhTests(TestCase):
    def setUp(self):
        self.stores = {}
        for nazev, kratky in (
            ('Vsetín', 'VS'),
            ('Zlín', 'ZL'),
            ('Přerov', 'PR'),
            ('Šternberk', 'ST'),
            ('Senimo', 'SE'),
            ('Globus', 'GL'),
        ):
            self.stores[store_key(nazev)] = Prodejna.objects.create(
                nazev=nazev,
                nazev_kratkiy=kratky,
                aktivni=True,
            )
        self.vsetin = self._user(91001, 'vyj.vs', 'Veselý', 'Vsetín', self.stores['vsetin'])
        self.globus = self._user(91002, 'vyj.gl', 'Globusová', 'Globus', self.stores['globus'])
        self.prerov = self._user(91003, 'vyj.pr', 'Přerovský', 'Přerov', self.stores['prerov'])
        self.admin = self._user(91004, 'vyj.admin', 'Admin', 'Ada', None, role='ADMIN')
        self.client = APIClient()

    def _user(self, pk, username, prijmeni, jmeno, store, role='PRODEJCE'):
        return WebUser.objects.create(
            id=pk,
            uzivatelske_jmeno=username,
            jmeno=jmeno,
            prijmeni=prijmeni,
            heslo='x',
            role=role,
            aktivni=True,
            prodejna_id=store.id if store else None,
        )

    def _occupy(self, store, days):
        self._brig_seq = getattr(self, '_brig_seq', 93000) + 1
        brig = WebUser.objects.create(
            id=self._brig_seq,
            uzivatelske_jmeno=f'brig.{store.id}',
            jmeno='Brig',
            prijmeni='Obsaz',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
            prodejna_id=store.id,
        )
        for day in days:
            Smena.objects.create(
                user=brig,
                prodejna=store,
                datum=day,
                cas_od=time(8, 0),
                cas_do=time(20, 0),
                typ_smeny='prace',
                pozice_smeny='prodej',
            )

    def test_due_months_okno(self):
        self.assertEqual(due_months(date(2026, 9, 29)), [])
        self.assertEqual(due_months(date(2026, 9, 30)), [(2026, 11)])
        self.assertEqual(due_months(date(2026, 10, 5)), [(2026, 11)])
        self.assertEqual(due_months(date(2026, 10, 8)), [])
        self.assertEqual(due_months(date(2026, 10, 31)), [(2026, 12)])

    def test_vsetin_jen_prerov_a_zlin_a_ne_po_sobe(self):
        for seed in range(12):
            VyjezdNavrh.objects.all().delete()
            VyjezdNotifikace.objects.all().delete()
            WebUser.objects.filter(id__in=(self.globus.id, self.prerov.id)).update(aktivni=False)
            dopln_vyjezdy(2026, 11, rng=random.Random(seed))
            rows = list(VyjezdNavrh.objects.filter(user=self.vsetin).order_by('datum'))
            self.assertEqual(len(rows), 2, seed)
            keys = {store_key(row.prodejna.nazev) for row in rows}
            self.assertTrue(keys <= {'prerov', 'zlin'}, keys)
            self.assertGreaterEqual(abs((rows[1].datum - rows[0].datum).days), 2)
            note = VyjezdNotifikace.objects.get(user=self.vsetin)
            self.assertIn('Počítej s nimi', note.message)
            self.assertIn('Listopad', note.message)

    def test_senimo_sobota_neni_ve_vyberu(self):
        self.stores['sternberk'].oteviraci_doba = _closed()
        self.stores['sternberk'].save(update_fields=['oteviraci_doba'])
        self.stores['prerov'].oteviraci_doba = _closed()
        self.stores['prerov'].save(update_fields=['oteviraci_doba'])
        self.stores['senimo'].oteviraci_doba = _hours({2, 4, 5})
        self.stores['senimo'].save(update_fields=['oteviraci_doba'])
        WebUser.objects.filter(id__in=(self.vsetin.id, self.prerov.id)).update(aktivni=False)
        for seed in range(15):
            VyjezdNavrh.objects.all().delete()
            dopln_vyjezdy(2026, 11, rng=random.Random(seed))
            rows = list(VyjezdNavrh.objects.filter(user=self.globus))
            self.assertEqual(len(rows), 2, seed)
            for row in rows:
                self.assertEqual(row.prodejna_id, self.stores['senimo'].id)
                self.assertNotEqual(row.datum.weekday(), 5, row.datum)

    def test_preferuje_neobsazene_dny(self):
        WebUser.objects.filter(id__in=(self.globus.id, self.prerov.id)).update(aktivni=False)
        volne = {date(2026, 11, 4), date(2026, 11, 18)}
        days = [
            date(2026, 11, day)
            for day in range(1, monthrange(2026, 11)[1] + 1)
            if date(2026, 11, day) not in volne
        ]
        self._occupy(self.stores['prerov'], days)
        self._occupy(self.stores['zlin'], days)
        dopln_vyjezdy(2026, 11, rng=random.Random(1))
        vybrane = set(VyjezdNavrh.objects.filter(user=self.vsetin).values_list('datum', flat=True))
        self.assertEqual(vybrane, volne)

    def test_druhy_beh_nepridava(self):
        WebUser.objects.filter(id__in=(self.globus.id, self.prerov.id)).update(aktivni=False)
        prvni = dopln_vyjezdy(2026, 11, rng=random.Random(1))
        druhy = dopln_vyjezdy(2026, 11, rng=random.Random(2))
        self.assertEqual(prvni['vytvoreno'], 2)
        self.assertEqual(druhy['vytvoreno'], 0)
        self.assertEqual(VyjezdNavrh.objects.filter(user=self.vsetin).count(), 2)

    def test_potvrzeni_nahradi_domaci_smenu(self):
        WebUser.objects.filter(id__in=(self.globus.id, self.prerov.id)).update(aktivni=False)
        dopln_vyjezdy(2026, 11, rng=random.Random(3))
        navrh = VyjezdNavrh.objects.filter(user=self.vsetin).order_by('datum').first()
        domaci = Smena.objects.create(
            user=self.vsetin,
            prodejna=self.stores['vsetin'],
            datum=navrh.datum,
            cas_od=time(8, 0),
            cas_do=time(20, 0),
            typ_smeny='prace',
            pozice_smeny='prodej',
        )
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/shifts/vyjezdy/potvrdit/', {'ids': [navrh.id]}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['vytvoreno'], 1)
        domaci.refresh_from_db()
        navrh.refresh_from_db()
        self.assertFalse(domaci.aktivni)
        self.assertEqual(navrh.stav, 'potvrzeno')
        self.assertEqual(navrh.smena.prodejna_id, navrh.prodejna_id)
        self.assertEqual(navrh.smena.pozice_smeny, 'prodej')

    def test_rucne_senimo_sobota_a_sternberk(self):
        WebUser.objects.filter(id__in=(self.globus.id, self.prerov.id)).update(aktivni=False)
        dopln_vyjezdy(2026, 11, rng=random.Random(4))
        rows = list(VyjezdNavrh.objects.filter(user=self.vsetin).order_by('datum'))
        sobota = next(
            date(2026, 11, day)
            for day in range(1, 31)
            if date(2026, 11, day).weekday() == 5 and abs((date(2026, 11, day) - rows[1].datum).days) >= 2
        )
        self.client.force_authenticate(user=self.admin)
        spatne = self.client.patch(
            f'/api/shifts/vyjezdy/{rows[0].id}/',
            {'datum': sobota.isoformat(), 'prodejna_id': self.stores['senimo'].id},
            format='json',
        )
        self.assertEqual(spatne.status_code, 400)
        self.assertIn('sobotu', spatne.data['error'])

        streda = next(
            date(2026, 11, day)
            for day in range(1, 31)
            if date(2026, 11, day).weekday() == 2 and abs((date(2026, 11, day) - rows[1].datum).days) >= 2
        )
        ok = self.client.patch(
            f'/api/shifts/vyjezdy/{rows[0].id}/',
            {'datum': streda.isoformat(), 'prodejna_id': self.stores['sternberk'].id},
            format='json',
        )
        self.assertEqual(ok.status_code, 200, ok.data)
        rows[0].refresh_from_db()
        self.assertEqual(rows[0].prodejna_id, self.stores['sternberk'].id)
        note = VyjezdNotifikace.objects.get(user=self.vsetin, read_at__isnull=True)
        self.assertIn('Šternberk', note.message)

    def test_vedouci_ze_zlin_cepkov_dostane_vyjezd(self):
        WebUser.objects.filter(id__in=(self.globus.id, self.prerov.id, self.vsetin.id)).update(aktivni=False)
        self.stores['zlin'].nazev = 'Zlín - Čepkov'
        self.stores['zlin'].nazev_kratkiy = 'Zlín'
        self.stores['zlin'].save(update_fields=['nazev', 'nazev_kratkiy'])
        vedouci = self._user(91021, 'vyj.ved', 'Kováčik', 'Lukáš', self.stores['zlin'], role='VEDOUCI')
        admin = self._user(91022, 'vyj.adm2', 'Admin', 'Druhý', self.stores['globus'], role='ADMIN')
        brig = self._user(91023, 'vyj.brig2', 'Brig', 'Druhý', self.stores['globus'], role='BRIGADNIK')
        dopln_vyjezdy(2026, 11, rng=random.Random(2))
        rows = list(VyjezdNavrh.objects.filter(user=vedouci, stav='navrh'))
        self.assertEqual(len(rows), 2)
        self.assertTrue({store_key(row.prodejna.nazev) for row in rows} <= {'vsetin', 'prerov'})
        self.assertFalse(VyjezdNavrh.objects.filter(user=admin).exists())
        self.assertFalse(VyjezdNavrh.objects.filter(user=brig).exists())

    def test_technik_a_testovaci_ucet_nedostanou_vyjezd(self):
        WebUser.objects.filter(id__in=(self.globus.id, self.prerov.id)).update(aktivni=False)
        vychodil = self._user(91011, 'vyj.vych', 'Vychodil', 'František', self.stores['vsetin'])
        dolak = self._user(91012, 'vyj.dol', 'Dolák', 'Tomáš', self.stores['zlin'])
        novy = self._user(91013, 'vyj.novy', 'prodejce', 'Nový', self.stores['prerov'])
        VyjezdNavrh.objects.create(
            user=dolak,
            mesic=date(2026, 11, 1),
            datum=date(2026, 11, 12),
            prodejna=self.stores['sternberk'],
            stav='navrh',
        )
        dopln_vyjezdy(2026, 11, rng=random.Random(1))
        self.assertFalse(VyjezdNavrh.objects.filter(user=vychodil, stav='navrh').exists())
        self.assertFalse(VyjezdNavrh.objects.filter(user=novy, stav='navrh').exists())
        self.assertFalse(VyjezdNavrh.objects.filter(user=dolak, stav='navrh').exists())
        self.assertEqual(VyjezdNavrh.objects.get(user=dolak).stav, 'zruseno')
        self.assertEqual(VyjezdNavrh.objects.filter(user=self.vsetin, stav='navrh').count(), 2)

    def test_kalendar_ukaze_navrh_kolegovi(self):
        VyjezdNavrh.objects.create(
            user=self.vsetin,
            mesic=date(2026, 11, 1),
            datum=date(2026, 11, 12),
            prodejna=self.stores['prerov'],
            stav='navrh',
        )
        self.client.force_authenticate(user=self.prerov)
        res = self.client.get(f'/api/shifts/calendar/?mesic=2026-11&prodejna={self.stores["prerov"].id}')
        self.assertEqual(res.status_code, 200, res.data)
        row = res.data['vyjezdy']['2026-11-12'][0]
        self.assertEqual(row['user_id'], self.vsetin.id)
        self.assertTrue(row['navrh'])
