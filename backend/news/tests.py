from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from users.models import WebUser
from news.models import Novinka, NewsUserVisitState


class NewsUnreadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = WebUser.objects.create(
            id=9101,
            uzivatelske_jmeno='autor_news',
            jmeno='Autor',
            prijmeni='Test',
            role='ADMIN',
            heslo='x',
        )
        self.reader = WebUser.objects.create(
            id=9102,
            uzivatelske_jmeno='ctenar_news',
            jmeno='Ctenar',
            prijmeni='Test',
            role='PRODEJCE',
            heslo='x',
        )
        self.client.force_authenticate(user=self.reader)

    def test_first_summary_initializes_visit_with_zero(self):
        Novinka.objects.create(autor=self.author, obsah='Stará novinka', aktivni=True)
        res = self.client.get('/api/news/unread-summary/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['unread_count'], 0)
        self.assertTrue(NewsUserVisitState.objects.filter(user_id=self.reader.id).exists())

    def test_unread_counts_new_posts_from_others(self):
        NewsUserVisitState.objects.create(
            user_id=self.reader.id,
            last_seen_at=timezone.now() - timedelta(hours=1),
        )
        Novinka.objects.create(autor=self.author, obsah='Nová', aktivni=True)
        Novinka.objects.create(autor=self.reader, obsah='Moje', aktivni=True)
        res = self.client.get('/api/news/unread-summary/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['unread_count'], 1)
        self.assertEqual(len(res.data['items']), 1)
        self.assertEqual(res.data['items'][0]['obsah'], 'Nová')

    def test_mark_all_read_clears_badge(self):
        NewsUserVisitState.objects.create(
            user_id=self.reader.id,
            last_seen_at=timezone.now() - timedelta(hours=1),
        )
        Novinka.objects.create(autor=self.author, obsah='Nová', aktivni=True)
        res = self.client.post('/api/news/mark-all-read/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['unread_count'], 0)
        res2 = self.client.get('/api/news/unread-summary/')
        self.assertEqual(res2.data['unread_count'], 0)
