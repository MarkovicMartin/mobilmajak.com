from django.test import TestCase
from rest_framework.test import APIClient

from coaching.aggregate import (
    COACHING_KATEGORIE_KODY,
    _build_kategorie_rows,
    _compute_benchmark,
    _compute_signaly,
)
from coaching.models import CoachingGoal, CoachingNote
from stores.models import Prodejna
from users.models import WebUser


def _make_user(pk, role, prodejna_id=None, **kwargs):
    defaults = {
        'uzivatelske_jmeno': f'coachuser{pk}',
        'jmeno': 'Test',
        'prijmeni': f'User{pk}',
        'heslo': 'x',
        'role': role,
        'aktivni': True,
        'moduly': [],
    }
    defaults.update(kwargs)
    user, _ = WebUser.objects.update_or_create(id=pk, defaults=defaults)
    if prodejna_id is not None:
        user.prodejna_id = prodejna_id
        user.save(update_fields=['prodejna_id'])
    return user


class CoachingKategorieTests(TestCase):
    def test_kategorie_bez_rodice_prislusenstvi(self):
        rows = _build_kategorie_rows(
            {'kategorie': {
                'PRISLUSENSTVI_SKLA': {'kusy': 10, 'obrat': 100},
                'PRISLUSENSTVI_OBALY': {'kusy': 5, 'obrat': 50},
                'NOVE_TELEFONY': {'kusy': 2, 'obrat': 200},
            }},
            {'PRISLUSENSTVI_SKLA': 8, 'NOVE_TELEFONY': 3},
        )
        kody = [r['kategorie_kod'] for r in rows]
        self.assertNotIn('PRISLUSENSTVI', kody)
        self.assertIn('PRISLUSENSTVI_SOUBR', kody)
        souhrn = next(r for r in rows if r['kategorie_kod'] == 'PRISLUSENSTVI_SOUBR')
        self.assertEqual(souhrn['skutecne_kusy'], 15)
        nove = next(r for r in rows if r['kategorie_kod'] == 'NOVE_TELEFONY')
        self.assertEqual(nove['skutecne_kusy'], 2)
        self.assertEqual(len([k for k in kody if k in COACHING_KATEGORIE_KODY]), len(COACHING_KATEGORIE_KODY))


class CoachingSignalyTests(TestCase):
    def test_signaly_from_cache(self):
        skut_cache = {
            (1, 2026, 3): {'obrat': 0, 'kategorie': {'NOVE_TELEFONY': {'kusy': 50, 'obrat': 0}}},
            (1, 2026, 4): {'obrat': 0, 'kategorie': {'NOVE_TELEFONY': {'kusy': 40, 'obrat': 0}}},
            (1, 2026, 5): {'obrat': 0, 'kategorie': {'NOVE_TELEFONY': {'kusy': 30, 'obrat': 0}}},
        }
        plan_cache = {
            (1, 2026, 3): (100, {'NOVE_TELEFONY': 100}),
            (1, 2026, 4): (100, {'NOVE_TELEFONY': 100}),
            (1, 2026, 5): (100, {'NOVE_TELEFONY': 100}),
        }
        signaly = _compute_signaly(1, 2026, 6, skut_cache, plan_cache)
        self.assertTrue(signaly['systematicky_pod_planem'])


class CoachingBenchmarkTests(TestCase):
    def test_compute_benchmark_ranking(self):
        rows = [
            {'id': 1, 'prodejna_id': 10, 'polozky_nad_100': 50},
            {'id': 2, 'prodejna_id': 10, 'polozky_nad_100': 30},
            {'id': 3, 'prodejna_id': 10, 'polozky_nad_100': 40},
        ]
        bench = _compute_benchmark(rows, 'polozky_nad_100')
        self.assertEqual(bench[1]['poradi'], 1)
        self.assertEqual(bench[1]['top_prodejce'], 50)
        self.assertEqual(bench[2]['poradi'], 3)
        self.assertAlmostEqual(bench[3]['prumer_prodejny'], 40)


class CoachingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_user(9101, 'ADMIN')
        self.vedouci_a = _make_user(9102, 'VEDOUCI')
        self.vedouci_b = _make_user(9103, 'VEDOUCI')
        self.prodejce = _make_user(9104, 'PRODEJCE', prodejna_id=201)

        self.store_a = Prodejna.objects.create(
            id=201,
            nazev='Coaching A',
            nazev_kratkiy='CA',
            vedouci_user_id=self.vedouci_a.id,
            aktivni=True,
        )
        self.store_b = Prodejna.objects.create(
            id=202,
            nazev='Coaching B',
            nazev_kratkiy='CB',
            vedouci_user_id=self.vedouci_b.id,
            aktivni=True,
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_prodejce_denied(self):
        self._auth(self.prodejce)
        res = self.client.get('/api/coaching/roster/')
        self.assertEqual(res.status_code, 403)

    def test_vedouci_roster_ok(self):
        self._auth(self.vedouci_a)
        res = self.client.get('/api/coaching/roster/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])

    def test_vedouci_cannot_access_other_store_seller(self):
        other = _make_user(9105, 'PRODEJCE', prodejna_id=202)
        self._auth(self.vedouci_a)
        res = self.client.get(f'/api/coaching/sellers/{other.id}/profile/')
        self.assertEqual(res.status_code, 403)

    def test_notes_crud(self):
        self._auth(self.vedouci_a)
        create = self.client.post(
            '/api/coaching/notes/',
            {'prodejce_id': self.prodejce.id, 'typ': 'poznamka', 'text': 'Poznámka k školení'},
            format='json',
        )
        self.assertEqual(create.status_code, 201)
        note_id = create.data['note']['id']
        self.assertEqual(CoachingNote.objects.filter(pk=note_id).count(), 1)

        patch = self.client.patch(
            f'/api/coaching/notes/{note_id}/',
            {'text': 'Upraveno'},
            format='json',
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(CoachingNote.objects.get(pk=note_id).text, 'Upraveno')

    def test_goals_create(self):
        self._auth(self.admin)
        res = self.client.post(
            '/api/coaching/goals/',
            {
                'prodejce_id': self.prodejce.id,
                'nazev': 'Zvýšit LOS',
                'kategorie_metrika': 'los',
                'stav': 'otevreny',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(CoachingGoal.objects.filter(prodejce_id=self.prodejce.id).count(), 1)
