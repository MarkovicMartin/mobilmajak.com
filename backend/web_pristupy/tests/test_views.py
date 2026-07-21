from django.test import TestCase
from rest_framework.test import APIClient

from users.models import WebUser
from web_pristupy.models import WEB_PRISTUPY_PRODEJNY


class WebPristupyPermissionsTest(TestCase):
    def setUp(self):
        self.admin = WebUser.objects.create(
            id=9921,
            uzivatelske_jmeno='admin.pristupy.test',
            jmeno='Admin',
            prijmeni='Test',
            heslo='x',
            role='ADMIN',
            aktivni=True,
        )
        self.prodejce = WebUser.objects.create(
            id=9922,
            uzivatelske_jmeno='prodejce.pristupy.test',
            jmeno='Jan',
            prijmeni='Prodejce',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
        )
        self.brigadnik = WebUser.objects.create(
            id=9923,
            uzivatelske_jmeno='brigadnik.pristupy.test',
            jmeno='Eva',
            prijmeni='Brigadnik',
            heslo='x',
            role='BRIGADNIK',
            aktivni=True,
        )
        self.access = WEB_PRISTUPY_PRODEJNY.objects.create(
            company_name='Import U',
            website_url='https://example.com',
            username='login@test.cz',
            password='heslo123',
            store='Globus',
            added_by='import',
        )
        self.client = APIClient()

    def test_admin_can_update_imported_access(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.put(
            f'/api/pristupy/{self.access.id}/',
            {
                'company_name': 'Import U',
                'website_url': 'https://example.com',
                'username': 'novy-login@test.cz',
                'password': 'heslo123',
                'store': 'Globus',
                'added_by': 'import',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.access.refresh_from_db()
        self.assertEqual(self.access.username, 'novy-login@test.cz')

    def test_admin_can_delete_imported_access(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(f'/api/pristupy/{self.access.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(
            WEB_PRISTUPY_PRODEJNY.objects.filter(id=self.access.id).exists()
        )

    def test_any_authenticated_user_can_update(self):
        for user in (self.prodejce, self.brigadnik):
            with self.subTest(role=user.role):
                self.client.force_authenticate(user=user)
                res = self.client.patch(
                    f'/api/pristupy/{self.access.id}/',
                    {'username': f'uprava-{user.role.lower()}'},
                    format='json',
                )
                self.assertEqual(res.status_code, 200)
                self.access.refresh_from_db()
                self.assertEqual(self.access.username, f'uprava-{user.role.lower()}')

    def test_non_admin_cannot_delete(self):
        self.client.force_authenticate(user=self.prodejce)
        delete_res = self.client.delete(f'/api/pristupy/{self.access.id}/')
        self.assertEqual(delete_res.status_code, 403)
        self.assertEqual(delete_res.data['error'], 'Pouze administrátor může mazat přístupy')
