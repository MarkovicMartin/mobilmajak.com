from django.core.management.base import BaseCommand

from finance.ocr_deps import check_finance_ocr_deps


class Command(BaseCommand):
    help = 'Ověří OCR závislosti pro automatické vyčítání VS a částek z FA'

    def handle(self, *args, **options):
        status = check_finance_ocr_deps()
        self.stdout.write(f"text PDF: {'OK' if status['text_pdf_ready'] else 'FAIL'}")
        self.stdout.write(f"scan OCR: {'OK' if status['scan_ocr_ready'] else 'FAIL'}")
        self.stdout.write(f"celkem ready: {'OK' if status['ready'] else 'FAIL'}")
        for key, val in status['components'].items():
            self.stdout.write(f"  {key}: {val}")
        for m in status['missing']:
            self.stdout.write(self.style.WARNING(f"  missing: {m}"))
        for n in status['notes']:
            self.stdout.write(self.style.NOTICE(f"  note: {n}"))
        if not status['ready']:
            self.stdout.write(self.style.ERROR(
                'Nainstaluj: ./scripts/install-finance-ocr.sh',
            ))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('OCR stack připraven.'))
