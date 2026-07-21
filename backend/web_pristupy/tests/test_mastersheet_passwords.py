from django.test import SimpleTestCase, TestCase

from web_pristupy.mastersheet_logins import (
    PLACEHOLDER_PASSWORD,
    build_password_index,
    needs_password_update,
    normalize_key,
    plan_password_updates,
    resolve_website_url,
)
from web_pristupy.models import WEB_PRISTUPY_PRODEJNY


class MastersheetPasswordLogicTests(SimpleTestCase):
    def test_needs_password_update(self):
        self.assertTrue(needs_password_update(''))
        self.assertTrue(needs_password_update(None))
        self.assertTrue(needs_password_update(PLACEHOLDER_PASSWORD))
        self.assertFalse(needs_password_update('skutecne-heslo'))

    def test_plan_updates_only_placeholders(self):
        ms = [
            {'store': 'GLOBUS', 'service': 'ADART', 'username': 'globus', 'password': 'heslo123'},
            {'store': 'GLOBUS', 'service': 'Gmail', 'username': 'x@y.cz', 'password': ''},
        ]
        index = build_password_index(ms)
        db_rows = [
            {'id': 1, 'store': 'Globus', 'company_name': 'ADART', 'username': 'globus', 'password': PLACEHOLDER_PASSWORD},
            {'id': 2, 'store': 'Globus', 'company_name': 'ADART', 'username': 'globus', 'password': 'rucni-heslo'},
            {'id': 3, 'store': 'Globus', 'company_name': 'Neexistuje', 'username': 'n/a', 'password': PLACEHOLDER_PASSWORD},
            {'id': 4, 'store': 'Globus', 'company_name': 'Gmail', 'username': 'x@y.cz', 'password': ''},
        ]
        plan = plan_password_updates(db_rows, index)
        self.assertEqual(len(plan['updated']), 1)
        self.assertEqual(plan['updated'][0]['new_password'], 'heslo123')
        self.assertEqual(len(plan['skipped_has_password']), 1)
        self.assertEqual(len(plan['skipped_no_match']), 2)
        self.assertEqual(len(plan['skipped_empty_excel']), 0)

    def test_normalize_key_matches_across_casing(self):
        key = normalize_key('GLOBUS', 'ADART', 'Globus')
        self.assertEqual(key, ('globus', 'adart', 'globus'))

    def test_resolve_website_url_from_full_url(self):
        self.assertEqual(
            resolve_website_url('https://lcdpartner.com/cs/'),
            'https://lcdpartner.com/cs/',
        )
        self.assertEqual(
            resolve_website_url('Google nakupy https://merchants.google.com/'),
            'https://merchants.google.com/',
        )

    def test_resolve_website_url_from_domain(self):
        self.assertEqual(resolve_website_url('doogee-shop.cz'), 'https://doogee-shop.cz')
        self.assertEqual(resolve_website_url('www.sammobile.com'), 'https://www.sammobile.com')
        self.assertEqual(resolve_website_url('Hurtel.pl'), 'https://Hurtel.pl')

    def test_resolve_website_url_rejects_legal_form(self):
        self.assertEqual(resolve_website_url('AT Computers a.s.'), '')
        self.assertEqual(resolve_website_url('GAMACZ s.r.o.'), '')
        self.assertEqual(resolve_website_url('Bonvision s.r.o. - XIAOMI ofic.distributor pro ČR'), '')


class ImportMastersheetPasswordsCommandTests(TestCase):
    def test_dry_run_updates_placeholder_in_db(self):
        row = WEB_PRISTUPY_PRODEJNY.objects.create(
            company_name='Test služba',
            website_url='https://example.com',
            username='testuser',
            password=PLACEHOLDER_PASSWORD,
            store='Globus',
            added_by='test',
        )
        ms = [
            {
                'store': 'GLOBUS',
                'service': 'Test služba',
                'username': 'testuser',
                'password': 'excel-heslo',
            }
        ]
        plan = plan_password_updates(
            [{'id': row.id, 'store': row.store, 'company_name': row.company_name,
              'username': row.username, 'password': row.password}],
            build_password_index(ms),
        )
        self.assertEqual(len(plan['updated']), 1)
        self.assertEqual(plan['updated'][0]['new_password'], 'excel-heslo')

        for item in plan['updated']:
            WEB_PRISTUPY_PRODEJNY.objects.filter(pk=item['id']).update(password=item['new_password'])

        row.refresh_from_db()
        self.assertEqual(row.password, 'excel-heslo')

    def test_does_not_overwrite_manual_password(self):
        row = WEB_PRISTUPY_PRODEJNY.objects.create(
            company_name='Ruční',
            website_url='https://example.com',
            username='manual',
            password='zachovat',
            store='Přerov',
            added_by='test',
        )
        ms = [{'store': 'PŘEROV', 'service': 'Ruční', 'username': 'manual', 'password': 'z-excelu'}]
        plan = plan_password_updates(
            [{'id': row.id, 'store': row.store, 'company_name': row.company_name,
              'username': row.username, 'password': row.password}],
            build_password_index(ms),
        )
        self.assertEqual(plan['updated'], [])
        self.assertEqual(len(plan['skipped_has_password']), 1)


class FillWebsiteUrlTests(TestCase):
    def test_fill_urls_updates_empty_website(self):
        row = WEB_PRISTUPY_PRODEJNY.objects.create(
            company_name='doogee-shop.cz',
            website_url='',
            username='info@mobilmajak.cz',
            password=PLACEHOLDER_PASSWORD,
            store='Globus',
            added_by='mastersheet-import',
        )
        url = resolve_website_url(row.company_name)
        self.assertEqual(url, 'https://doogee-shop.cz')
        WEB_PRISTUPY_PRODEJNY.objects.filter(pk=row.id).update(website_url=url)
        row.refresh_from_db()
        self.assertEqual(row.website_url, 'https://doogee-shop.cz')
