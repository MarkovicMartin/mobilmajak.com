from django.core.management.base import BaseCommand

from analytics.zasilkovna_leaderboard_cache import refresh_after_packeta_import


class Command(BaseCommand):
    help = 'Přepočítá cache Zásilkovna pro žebříček (dnes + aktuální měsíc).'

    def handle(self, *args, **options):
        result = refresh_after_packeta_import(source='manage_command')
        if not result.get('ok'):
            self.stderr.write(self.style.ERROR('Přepočet selhal – viz logy.'))
            return
        for period in result.get('periods') or []:
            self.stdout.write(self.style.SUCCESS(
                f'{period["period_key"]}: {period["prodejcu"]} prodejců, '
                f'{period["prodejen"]} prodejen ({period["date_from"]}–{period["date_to"]})'
            ))
