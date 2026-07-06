from django.core.management.base import BaseCommand

from finance.faktura_process import process_doklad_ocr
from finance.models import FinanceDoklad


class Command(BaseCommand):
    help = 'Zpracuje OCR / extrakci u faktur ve stavu ceka_na_ocr'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--doklad-id', type=int, default=0)

    def handle(self, *args, **options):
        if options['doklad_id']:
            process_doklad_ocr(options['doklad_id'])
            self.stdout.write(self.style.SUCCESS(f'OK doklad {options["doklad_id"]}'))
            return

        qs = FinanceDoklad.objects.filter(
            stav=FinanceDoklad.STAV_CEKA_NA_OCR,
        ).order_by('vytvoreno')[: options['limit']]
        count = 0
        for d in qs:
            process_doklad_ocr(d.id)
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Zpracováno {count} dokladů'))
