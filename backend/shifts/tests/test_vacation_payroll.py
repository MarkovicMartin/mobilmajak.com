"""Testy fondu dovolené a výpočtu výplaty."""
from datetime import date, time, timedelta
from decimal import Decimal

from django.test import TestCase

from shifts.labor_hours import fondu_hodin_mesic
from shifts.models import Smena
from shifts.payroll_service import (
    build_payroll_row,
    dovolena_body_vypocet,
    prescas_body_vypocet,
    prumer_fixni_hodinove_body,
)
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
    is_pracovni_den,
    mesicni_cerpani_dovolene,
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
        stav = dovolena_stav(user, 2027)
        self.assertEqual(stav['odeceno_deficit_h'], deficit)
        self.assertEqual(stav['cerpano_smeny_h'], 0)
        self.assertEqual(stav['cerpano_h'], deficit)
        self.assertEqual(stav['zbyva_h'], round(DOVOLENA_ROCNI_FOND - deficit, 2))

    def test_deficit_nekrati_dovolenou_smenou(self):
        """Dovolená směna v měsíci se do deficitu nepočítá dvakrát."""
        user = WebUser.objects.create(
            id=9016, uzivatelske_jmeno='test_def2', jmeno='Def2', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2025, 2, 3),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
        )
        self.assertEqual(deficit_mesic_hodin(user.id, 2025, 2), 0)
        self.assertEqual(cerpana_dovolena_rok(user.id, 2025), DOVOLENA_HODINY_ZA_DEN)
        stav = dovolena_stav(user, 2025)
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
        rok_deficit = deficit_fondu_rok(user.id, dnes.year, referencni_datum=dnes)
        self.assertEqual(rok_deficit, 0)

    def test_validace_respektuje_deficit(self):
        user = WebUser.objects.create(
            id=9018, uzivatelske_jmeno='test_def4', jmeno='Def4', prijmeni='Test',
            heslo='x', role='PRODEJCE', aktivni=True, prodejna_id=self.prodejna.id,
        )
        fond_leden = fondu_hodin_mesic(2027, 1)
        Smena.objects.create(
            user=user, prodejna=self.prodejna, datum=date(2027, 1, 6),
            cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='prace',
        )
        deficit = fond_leden - DOVOLENA_HODINY_ZA_DEN
        workdays = []
        d = date(2027, 2, 1)
        while len(workdays) < 25:
            if is_pracovni_den(d):
                workdays.append(d)
            d += timedelta(days=1)
        volnych_h = DOVOLENA_ROCNI_FOND - deficit
        for wd in workdays[: int(volnych_h / DOVOLENA_HODINY_ZA_DEN)]:
            Smena.objects.create(
                user=user, prodejna=self.prodejna, datum=wd,
                cas_od=time(8, 0), cas_do=time(16, 0), typ_smeny='dovolena',
            )
        self.assertAlmostEqual(celkove_cerpano_rok(user.id, 2027), DOVOLENA_ROCNI_FOND, places=0)
        err = validate_dovolena_kapacita(user, workdays[int(volnych_h / DOVOLENA_HODINY_ZA_DEN)], 'dovolena')
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
        row = mesicni_cerpani_dovolene(user.id, 2025, 3, referencni_datum=date(2025, 12, 31))
        self.assertEqual(row['dovolena_smeny_h'], DOVOLENA_HODINY_ZA_DEN)
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
        stav = dovolena_stav(user, 2026)
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
        stav = dovolena_stav(user, 2026)
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
        stav = dovolena_stav(user, 2026)
        self.assertEqual(stav['cerpano_smeny_h'], DOVOLENA_HODINY_ZA_DEN)
        self.assertEqual(stav['odeceno_deficit_h'], 0)
        self.assertEqual(stav['cerpano_h'], DOVOLENA_HODINY_ZA_DEN)


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

    def test_build_payroll_row_includes_cestovne(self):
        row = build_payroll_row(
            self.user, 2026, 6,
            {self.user.id: {'odpracovano_h': 0, 'dovolena_h': 8, 'nemoc_h': 0, 'svatek_h': 0}},
            date(2026, 6, 1),
            {self.prodejna.id: 'Test2'},
            fondu_hodin_mesic(2026, 6),
            {}, {}, {},
        )
        self.assertEqual(row['cestovne_body'], 500.0)
        self.assertGreater(row['dovolena_body'], 0)
        self.assertEqual(
            row['celkem_body'],
            row['mzda_fixni_body'] + row['provize_body'] + row['odmena_mesic_body']
            + row['dovolena_body'] + row['prescas_body'] + row['cestovne_body']
            + row.get('dyska_body', 0) + row.get('pol_dok_odmena_body', 0),
        )
