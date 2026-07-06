"""Testy fondu dovolené a výpočtu výplaty."""
from datetime import date, time, timedelta
from decimal import Decimal

from django.test import TestCase

from shifts.labor_hours import fondu_hodin_mesic
from shifts.models import Smena
from shifts.payroll_service import (
    build_payroll_row,
    dovolena_body_vypocet,
    prumer_dovolena_hodinove_body,
    prumer_dovolena_hodinove_detail,
    prumer_fixni_hodinove_body,
    prescas_body_vypocet,
)
from shifts.prumer_mzdy_override import prumer_override_for_user
from shifts.vacation_service import (
    DOVOLENA_DEFICIT_OD_MESIC,
    DOVOLENA_DEFICIT_OD_ROK,
    DOVOLENA_HODINY_ZA_DEN,
    DOVOLENA_PREVOD_MAX,
    DOVOLENA_ROCNI_FOND,
    build_hours_cache_for_overview,
    build_vacation_overview_user,
    celkove_cerpano_rok,
    cerpana_dovolena_rok,
    deficit_fondu_rok,
    deficit_mesic_hodin,
    deficit_mesic_pro_dovolenou,
    dovolena_fond_rok,
    dovolena_hodin_ze_smeny,
    dovolena_stav,
    is_dovolena_eligible,
    is_dovolena_admin_user,
    is_dovolena_overview_user,
    is_pracovni_den,
    mesicni_cerpani_dovolene,
    pocita_deficit_z_fondu,
    prevod_z_predchoziho_roku,
    validate_dovolena_kapacita,
    _mesic_pocita_deficit,
)
from stores.models import Prodejna
from users.models import WebUser


class VacationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9001, nazev='Test', nazev_kratkiy='TST', aktivni=True,
        )
        cls.user = WebUser.objects.create(
            id=9001,
            uzivatelske_jmeno='test_dov',
            jmeno='Test',
            prijmeni='Dovolená',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
            mzda_zaklad=Decimal('14000'),
            mzda_doplnky=[],
        )

    def _make_smena(self, datum, typ='dovolena'):
        return Smena.objects.create(
            user=self.user,
            prodejna=self.prodejna,
            datum=datum,
            cas_od=time(8, 0),
            cas_do=time(16, 0),
            typ_smeny=typ,
        )

    def test_dovolena_8h_workday(self):
        smena = self._make_smena(date(2026, 6, 3))  # středa
        self.assertEqual(dovolena_hodin_ze_smeny(smena), DOVOLENA_HODINY_ZA_DEN)

    def test_dovolena_8h_weekend(self):
        smena = self._make_smena(date(2026, 6, 6))  # sobota
        self.assertEqual(dovolena_hodin_ze_smeny(smena), DOVOLENA_HODINY_ZA_DEN)

    def test_dovolena_8h_holiday(self):
        smena = self._make_smena(date(2026, 5, 1))  # svátek práce
        self.assertEqual(dovolena_hodin_ze_smeny(smena), DOVOLENA_HODINY_ZA_DEN)

    def test_fond_a_validace(self):
        user = WebUser.objects.create(
            id=9011, uzivatelske_jmeno='test_val', jmeno='Val', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        workdays = []
        d = date(2027, 1, 1)
        while len(workdays) < 21:
            if is_pracovni_den(d):
                workdays.append(d)
            d += timedelta(days=1)
        for wd in workdays[:20]:
            Smena.objects.create(
                user=user, prodejna=self.prodejna, datum=wd,
                cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
            )
        cerpano = cerpana_dovolena_rok(user.id, 2027)
        self.assertEqual(cerpano, 20 * DOVOLENA_HODINY_ZA_DEN)
        err = validate_dovolena_kapacita(user, workdays[20], 'dovolena')
        self.assertIsNotNone(err)

    def test_prevod_max_40(self):
        user = WebUser.objects.create(
            id=9012, uzivatelske_jmeno='test_prev', jmeno='Prev', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        self.assertEqual(prevod_z_predchoziho_roku(user.id, 2028), 0)
        fond = dovolena_fond_rok(user.id, 2028)
        self.assertEqual(fond, DOVOLENA_ROCNI_FOND)

    def test_prevod_carryover_capped_at_40(self):
        """Nevyčerpaný zbytek max 40 h se převádí do dalšího roku."""
        user = WebUser.objects.create(
            id=9013, uzivatelske_jmeno='test_carry', jmeno='Carry', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        workdays_2025 = []
        d = date(2025, 1, 1)
        while len(workdays_2025) < 15:
            if is_pracovni_den(d):
                workdays_2025.append(d)
            d += timedelta(days=1)
        for wd in workdays_2025:
            Smena.objects.create(
                user=user, prodejna=self.prodejna, datum=wd,
                cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
            )
        self.assertEqual(prevod_z_predchoziho_roku(user.id, 2026), DOVOLENA_PREVOD_MAX)
        self.assertEqual(dovolena_fond_rok(user.id, 2026), DOVOLENA_ROCNI_FOND + DOVOLENA_PREVOD_MAX)

    def test_stav(self):
        user = WebUser.objects.create(
            id=9014, uzivatelske_jmeno='test_stav', jmeno='Stav', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        stav = dovolena_stav(user, 2029)
        self.assertEqual(stav['fond_h'], DOVOLENA_ROCNI_FOND)
        self.assertEqual(stav['zbyva_h'], DOVOLENA_ROCNI_FOND)

    def test_deficit_mesic_odecita_z_dovolene(self):
        """Nesplněný měsíční fond snižuje roční zůstatek dovolené."""
        user = WebUser.objects.create(
            id=9015, uzivatelske_jmeno='test_def', jmeno='Def', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        fond_leden = fondu_hodin_mesic(2027, 1)
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2027, 1, 6),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='prace',
        )
        deficit = deficit_mesic_hodin(user.id, 2027, 1)
        self.assertEqual(deficit, round(fond_leden - 8, 2))
        stav = dovolena_stav(user, 2027, referencni_datum=date(2027, 2, 1))
        self.assertEqual(stav['odeceno_deficit_h'], deficit)
        self.assertEqual(stav['cerpano_smeny_h'], 0)
        self.assertEqual(stav['cerpano_h'], deficit)
        self.assertEqual(stav['zbyva_h'], round(DOVOLENA_ROCNI_FOND - deficit, 2))

    def test_deficit_nekrati_dovolenou_smenou(self):
        """Směna dovolené je ve výpisu; čerpání jde z deficitu fondu (bez práce = celý měsíc)."""
        user = WebUser.objects.create(
            id=9016, uzivatelske_jmeno='test_def2', jmeno='Def2', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2025, 2, 3),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
        )
        fond_unor = fondu_hodin_mesic(2025, 2)
        self.assertEqual(deficit_mesic_hodin(user.id, 2025, 2), fond_unor)
        self.assertEqual(cerpana_dovolena_rok(user.id, 2025), DOVOLENA_HODINY_ZA_DEN)
        stav = dovolena_stav(user, 2025)
        self.assertEqual(stav['cerpano_smeny_h'], DOVOLENA_HODINY_ZA_DEN)
        self.assertEqual(stav['cerpano_h'], DOVOLENA_HODINY_ZA_DEN)
        self.assertEqual(stav['zbyva_h'], DOVOLENA_ROCNI_FOND - DOVOLENA_HODINY_ZA_DEN)

    def test_deficit_jen_ukoncene_mesice(self):
        """Aktuální měsíc se do ročního deficitu nezapočítává."""
        user = WebUser.objects.create(
            id=9017, uzivatelske_jmeno='test_def3', jmeno='Def3', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        dnes = date.today()
        shift_datum = date(dnes.year, dnes.month, 1)
        while shift_datum.month == dnes.month and not is_pracovni_den(shift_datum):
            shift_datum += timedelta(days=1)
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=shift_datum,
            cas_od=time(8, 0), cas_do=time(12, 0), typ_smeny='prace',
        )
        mesicni_deficit = deficit_mesic_hodin(user.id, dnes.year, dnes.month)
        self.assertGreater(mesicni_deficit, 0)
        rok_deficit = deficit_fondu_rok(
            user.id, dnes.year, referencni_datum=date(dnes.year, 1, 1),
        )
        self.assertEqual(rok_deficit, 0)

    def test_validace_respektuje_kapacitu(self):
        """Po vyčerpání fondu přes směny dovolené nelze přidat další."""
        user = WebUser.objects.create(
            id=9018, uzivatelske_jmeno='test_def4', jmeno='Def4', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        workdays = []
        d = date(2027, 2, 1)
        while len(workdays) < 22:
            if is_pracovni_den(d):
                workdays.append(d)
            d += timedelta(days=1)
        for wd in workdays[:20]:
            Smena.objects.create(
                user=user, prodejna=self.prodejna, datum=wd,
                cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
            )
        self.assertEqual(cerpana_dovolena_rok(user.id, 2027), 20 * DOVOLENA_HODINY_ZA_DEN)
        err = validate_dovolena_kapacita(user, workdays[20], 'dovolena')
        self.assertIsNotNone(err)

    def test_mesicni_cerpani(self):
        user = WebUser.objects.create(
            id=9019, uzivatelske_jmeno='test_mes', jmeno='Mes', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2025, 3, 3),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
        )
        row = mesicni_cerpani_dovolene(
            user.id, 2025, 3, user=user, referencni_datum=date(2025, 12, 31),
        )
        self.assertEqual(row['dovolena_smeny_h'], DOVOLENA_HODINY_ZA_DEN)
        self.assertEqual(row['deficit_h'], 0)
        self.assertEqual(row['cerpano_h'], DOVOLENA_HODINY_ZA_DEN)

    def test_build_hours_cache_for_overview(self):
        cache = build_hours_cache_for_overview(2026, referencni_datum=date(2026, 6, 15))
        self.assertIn((2026, 6), cache)
        self.assertIn((2026, 5), cache)
        self.assertIsInstance(cache[(2026, 6)], dict)

    def test_build_vacation_overview_user(self):
        user = WebUser.objects.create(
            id=9020, uzivatelske_jmeno='test_over', jmeno='Over', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
            mzda_zaklad=Decimal('14000'),
        )
        overview = build_vacation_overview_user(
            user, 2026, referencni_datum=date(2026, 6, 15),
            hours_cache=build_hours_cache_for_overview(2026, referencni_datum=date(2026, 6, 15)),
            prumer_cache={},
        )
        self.assertIsNotNone(overview)
        self.assertEqual(overview['rok'], 2026)
        self.assertEqual(len(overview['mesice']), 12)
        self.assertGreater(overview['prumer_fixni_h'], 0)
        self.assertEqual(overview['dovolena_sazba_h'], overview['prumer_fixni_h'])

    def test_mesic_pocita_deficit_cutoff(self):
        self.assertFalse(_mesic_pocita_deficit(2025, 12))
        self.assertFalse(_mesic_pocita_deficit(DOVOLENA_DEFICIT_OD_ROK, 1))
        self.assertFalse(_mesic_pocita_deficit(DOVOLENA_DEFICIT_OD_ROK, DOVOLENA_DEFICIT_OD_MESIC - 1))
        self.assertTrue(_mesic_pocita_deficit(DOVOLENA_DEFICIT_OD_ROK, DOVOLENA_DEFICIT_OD_MESIC))
        self.assertTrue(_mesic_pocita_deficit(2027, 1))

    def test_deficit_pred_cervnem_2026_ignorovan(self):
        """Nesplněný fond před červnem 2026 se neodečítá z dovolené."""
        user = WebUser.objects.create(
            id=9021, uzivatelske_jmeno='test_cutoff', jmeno='Cut', prijmeni='Off',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2026, 1, 6),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='prace',
        )
        raw_deficit = deficit_mesic_hodin(user.id, 2026, 1)
        self.assertGreater(raw_deficit, 0)
        self.assertEqual(deficit_mesic_pro_dovolenou(user.id, 2026, 1), 0)
        stav = dovolena_stav(user, 2026, referencni_datum=date(2026, 1, 31))
        self.assertEqual(stav['odeceno_deficit_h'], 0)
        self.assertEqual(stav['cerpano_h'], 0)
        row = mesicni_cerpani_dovolene(user.id, 2026, 1, referencni_datum=date(2026, 12, 31))
        self.assertEqual(row['deficit_h'], 0)
        self.assertEqual(row['cerpano_h'], 0)

    def test_deficit_od_cervna_2026_pocita(self):
        user = WebUser.objects.create(
            id=9022, uzivatelske_jmeno='test_cutoff2', jmeno='Cut2', prijmeni='Off',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        fond_cerven = fondu_hodin_mesic(2026, 6)
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2026, 6, 1),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='prace',
        )
        deficit = deficit_mesic_pro_dovolenou(user.id, 2026, 6)
        self.assertEqual(deficit, round(fond_cerven - 8, 2))
        stav = dovolena_stav(user, 2026, referencni_datum=date(2026, 7, 1))
        self.assertEqual(stav['odeceno_deficit_h'], deficit)

    def test_dovolena_smena_pred_cervnem_stale_pocita(self):
        user = WebUser.objects.create(
            id=9023, uzivatelske_jmeno='test_cutoff3', jmeno='Cut3', prijmeni='Off',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2026, 3, 2),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
        )
        stav = dovolena_stav(user, 2026, referencni_datum=date(2026, 4, 1))
        self.assertEqual(stav['cerpano_smeny_h'], DOVOLENA_HODINY_ZA_DEN)
        self.assertEqual(stav['odeceno_deficit_h'], 0)
        self.assertEqual(stav['cerpano_h'], DOVOLENA_HODINY_ZA_DEN)

    def test_deficit_prescas_nekrati_fond(self):
        """Přesčas nad měsíční fond se do deficitu nezapočítává."""
        user = WebUser.objects.create(
            id=9024, uzivatelske_jmeno='test_ot', jmeno='OT', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        fond = fondu_hodin_mesic(2027, 1)
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2027, 1, 6),
            cas_od=time(8, 0), cas_do=time(22, 0), typ_smeny='prace',
        )
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2027, 1, 7),
            cas_od=time(8, 0), cas_do=time(22, 0), typ_smeny='prace',
        )
        deficit = deficit_mesic_hodin(user.id, 2027, 1)
        self.assertEqual(deficit, round(fond - 28, 2))

    def test_michaela_s_deficit_nezapocitava(self):
        """Michaela Smčková – backoffice i při přiřazené prodejně."""
        user = WebUser.objects.create(
            id=9026, uzivatelske_jmeno='michaela.smckova', jmeno='Michaela', prijmeni='Smčková',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        self.assertFalse(pocita_deficit_z_fondu(user))

    def test_backoffice_jen_smeny_dovolene(self):
        """Backoffice bez prodejny – čerpá jen ze směn dovolené, ne z deficitu fondu."""
        user = WebUser.objects.create(
            id=9025, uzivatelske_jmeno='test_bo', jmeno='Back', prijmeni='Office',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=None,
        )
        self.assertFalse(pocita_deficit_z_fondu(user))
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2027, 6, 2),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
        )
        stav = dovolena_stav(user, 2027)
        self.assertEqual(stav['cerpano_smeny_h'], DOVOLENA_HODINY_ZA_DEN)
        self.assertEqual(stav['odeceno_deficit_h'], 0)
        self.assertEqual(stav['cerpano_h'], DOVOLENA_HODINY_ZA_DEN)

    def test_admin_dovolena_jen_ze_smen(self):
        user = WebUser.objects.create(
            id=9027, uzivatelske_jmeno='admin.dov', jmeno='Admin', prijmeni='Dovolená',
            heslo='x', role='ADMIN', aktivni=True,
        )
        self.assertFalse(is_dovolena_eligible(user))
        self.assertTrue(is_dovolena_admin_user(user))
        self.assertTrue(is_dovolena_overview_user(user))
        self.assertFalse(pocita_deficit_z_fondu(user))
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2027, 7, 1),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
        )
        stav = dovolena_stav(user, 2027)
        self.assertEqual(stav['cerpano_h'], DOVOLENA_HODINY_ZA_DEN)
        self.assertEqual(stav['odeceno_deficit_h'], 0)

    def test_vacation_overview_queryset_includes_admin(self):
        from users.exclusions import vacation_overview_users_queryset
        WebUser.objects.create(
            id=9028, uzivatelske_jmeno='admin.overview', jmeno='Přehled', prijmeni='Admin',
            heslo='x', role='ADMIN', aktivni=True,
        )
        WebUser.objects.create(
            id=9029, uzivatelske_jmeno='admin.systemovy', jmeno='Administrátor', prijmeni='Systémový',
            heslo='x', role='ADMIN', aktivni=True,
        )
        ids = set(vacation_overview_users_queryset().values_list('id', flat=True))
        self.assertIn(9028, ids)
        self.assertNotIn(9029, ids)


class PayrollComputationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prodejna = Prodejna.objects.create(
            id=9002, nazev='Test2', nazev_kratkiy='TS2', aktivni=True,
        )
        cls.user = WebUser.objects.create(
            id=9002,
            uzivatelske_jmeno='test_pay',
            jmeno='Pay',
            prijmeni='Roll',
            heslo='x',
            role='PRODEJCE',
            aktivni=True,
            prodejna_id=cls.prodejna.id,
            mzda_zaklad=Decimal('14000'),
            mzda_doplnky=[{'kod': 'x', 'nazev': 'Doplněk', 'castka': 1000}],
            mzda_cestovne=Decimal('500'),
        )

    def test_prescas_body(self):
        fond = fondu_hodin_mesic(2026, 6)
        body, sazba, zaklad_vp = prescas_body_vypocet(self.user, 10, fond)
        expected_zaklad = Decimal('15000')  # 14000 + doplněk 1000, bez cestovného
        from decimal import ROUND_HALF_UP
        expected_sazba = (expected_zaklad / Decimal(str(fond))).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        expected = (expected_zaklad * Decimal('10') / Decimal(str(fond))).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.assertEqual(zaklad_vp, expected_zaklad)
        self.assertEqual(sazba, expected_sazba)
        self.assertEqual(body, expected)

    def test_dovolena_body(self):
        prumer = Decimal('100')
        body = dovolena_body_vypocet(self.user, 16, prumer)
        self.assertEqual(body, Decimal('1600'))

    def test_prumer_fallback(self):
        prumer = prumer_fixni_hodinove_body(self.user, 2026, 6)
        fond = fondu_hodin_mesic(2026, 6)
        from decimal import ROUND_HALF_UP
        expected = (Decimal('14000') / Decimal(str(fond))).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.assertEqual(prumer, expected)

    def test_prumer_dovolena_vsechny_slozky_vyplaty(self):
        """Průměr: základ + provize po srážkách + odměna + položky/účtenku."""
        user = WebUser.objects.create(
            id=9026, uzivatelske_jmeno='test_prum', jmeno='Prum', prijmeni='Er',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
            mzda_zaklad=Decimal('14000'),
            mzda_doplnky=[],
        )
        h = Decimal('160')
        prumer_cache = {
            (2026, 3): {
                user.id: {
                    'provize_brutto': Decimal('10000'),
                    'provize_net': Decimal('9000'),
                    'penalizace_srazka': Decimal('1000'),
                    'odmena_mesic': Decimal('5000'),
                    'pol_dok_odmena': Decimal('1000'),
                },
            },
        }
        prumer = prumer_dovolena_hodinove_body(
            user, 2026, 6, override_mesice=[
                {'rok': 2026, 'mesic': 3, 'odpracovano_h': float(h)},
            ],
            prumer_cache=prumer_cache,
        )
        expected = ((Decimal('14000') + Decimal('9000') + Decimal('5000') + Decimal('1000')) / h).quantize(Decimal('1'))
        self.assertEqual(prumer, expected)

    def test_build_payroll_row_includes_cestovne(self):
        fond = fondu_hodin_mesic(2026, 6)
        row = build_payroll_row(
            self.user, 2026, 6,
            {self.user.id: {'odpracovano_h': 0, 'dovolena_h': 8, 'nemoc_h': 0, 'svatek_h': 0}},
            date(2026, 6, 1),
            {self.prodejna.id: 'Test2'},
            fond,
            {}, {}, {},
            prumer_cache={},
        )
        self.assertEqual(row['cestovne_body'], 500.0)
        self.assertEqual(row['dovolena_smeny_h'], 8)
        self.assertEqual(row['dovolena_h'], fond)
        self.assertEqual(row['deficit_h'], fond)
        self.assertGreater(row['dovolena_body'], 0)
        self.assertEqual(
            row['celkem_body'],
            row['mzda_fixni_body'] + row['provize_body'] + row['odmena_mesic_body']
            + row['dovolena_body'] + row['prescas_body'] + row['cestovne_body']
            + row.get('dyska_body', 0) + row.get('pol_dok_odmena_body', 0),
        )

    def test_build_payroll_row_dovolena_z_deficitu_fondu(self):
        """Proplácí se celý deficit fondu, ne jen hodiny ze směn dovolené."""
        fond = fondu_hodin_mesic(2026, 6)
        odpracovano = 120.0
        deficit = round(fond - odpracovano, 2)
        dovolena_smeny = 48.0
        row = build_payroll_row(
            self.user, 2026, 6,
            {self.user.id: {
                'odpracovano_h': odpracovano,
                'dovolena_h': dovolena_smeny,
                'nemoc_h': 0,
                'svatek_h': 0,
            }},
            date(2026, 6, 1),
            {self.prodejna.id: 'Test2'},
            fond,
            {}, {}, {},
            prumer_cache={},
        )
        self.assertEqual(row['dovolena_smeny_h'], dovolena_smeny)
        self.assertEqual(row['deficit_h'], deficit)
        self.assertEqual(row['dovolena_h'], deficit)
        self.assertNotEqual(row['dovolena_h'], dovolena_smeny)
        expected_body = float(
            dovolena_body_vypocet(self.user, deficit, Decimal(str(row['prumer_fixni_h'])))
        )
        self.assertEqual(row['dovolena_body'], expected_body)

    def test_build_payroll_row_pouziva_excel_override_prumeru(self):
        user = WebUser.objects.create(
            id=9027, uzivatelske_jmeno='test_kolar', jmeno='Adam', prijmeni='Kolarčík',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
            mzda_zaklad=Decimal('14000'),
        )
        override = prumer_override_for_user(user)
        self.assertIsNotNone(override)
        self.assertEqual(len(override), 3)
        fond = fondu_hodin_mesic(2026, 6)
        row = build_payroll_row(
            user, 2026, 6,
            {user.id: {'odpracovano_h': 120, 'dovolena_h': 48, 'nemoc_h': 0, 'svatek_h': 0}},
            date(2026, 6, 1),
            {self.prodejna.id: 'Test2'},
            fond,
            {}, {}, {},
            prumer_cache={},
        )
        detail = row['prumer_dovolena_detail']
        self.assertEqual(detail['zdroj'], 'override_excel')
        self.assertEqual(detail['celkem_h'], sum(m['odpracovano_h'] for m in override))
        detail_bez_override = prumer_dovolena_hodinove_detail(user, 2026, 6, prumer_cache={})
        self.assertNotEqual(row['prumer_dovolena_h'], float(detail_bez_override['prumer_h']))
