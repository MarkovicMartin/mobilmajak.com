from datetime import date, time

from django.test import SimpleTestCase

from shifts.smeny_excel_shift_import import (
    detect_shift_type,
    infer_shift_times,
    parse_excel_time_cell,
    resolve_store_label,
    shift_surname_key,
)


class SmenyExcelShiftImportTest(SimpleTestCase):
    def test_shift_surname_key_nemoc(self):
        self.assertEqual(shift_surname_key('Benny Nemocenská'), 'babušík')

    def test_parse_excel_time_float(self):
        self.assertEqual(parse_excel_time_cell(8.0), time(8, 0))
        self.assertEqual(parse_excel_time_cell(20.0), time(20, 0))

    def test_parse_excel_time_absent(self):
        self.assertIsNone(parse_excel_time_cell('x'))

    def test_infer_shift_times_from_hours(self):
        cas_od, cas_do = infer_shift_times(None, None, 12.0, 'prace')
        self.assertEqual(cas_od, time(8, 0))
        self.assertEqual(cas_do, time(20, 0))

    def test_detect_shift_type(self):
        self.assertEqual(detect_shift_type('Novák dovolená', None, 8), 'dovolena')
        self.assertEqual(detect_shift_type('Novák', 'Přerov', 8), 'prace')

    def test_resolve_store_label(self):
        store, note = resolve_store_label('Servis GL', 'Globus')
        self.assertEqual(store, 'Globus')
        self.assertEqual(note, 'Servis GL')

        store2, note2 = resolve_store_label(None, 'Šternberk')
        self.assertEqual(store2, 'Šternberk')
        self.assertEqual(note2, '')

    def test_infer_absence_times(self):
        cas_od, cas_do = infer_shift_times(None, None, 0, 'nemoc')
        self.assertEqual((cas_od, cas_do), (time(8, 0), time(16, 0)))
