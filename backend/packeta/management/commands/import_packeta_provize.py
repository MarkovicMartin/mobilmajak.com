from django.core.management.base import BaseCommand, CommandError

from packeta.packeta_fetch import (
    default_chunk_days,
    fetch_and_import_all_branches,
    fetch_and_import_branch,
    import_packeta_rows,
)
from packeta.packeta_parser import parse_packeta_csv
from packeta.secrets import get_packeta_admin_for_fetch


class Command(BaseCommand):
    help = (
        'Import Packeta provize – CSV soubor, nebo --fetch '
        '(doporučeno: --period month --prodejna-id N)'
    )

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Cesta k provize.csv')
        parser.add_argument('--prodejna-id', type=int, help='ID prodejny 1–6')
        parser.add_argument('--fetch', action='store_true', help='Stáhnout z admin.packeta.com')
        parser.add_argument(
            '--period',
            choices=['month', 'yesterday', 'days'],
            default='month',
            help='Období: month=tento kalendářní měsíc, yesterday=včera, days=--days zpět',
        )
        parser.add_argument(
            '--typ',
            choices=['baliky', 'podani', 'vydane'],
            default='baliky',
            help='Typ provize: baliky=vše (4 typy), podani=Podání+C2C, vydane=Zpracování',
        )
        parser.add_argument('--all-branches', action='store_true', help='Všechny pobočky 1–6')
        parser.add_argument('--days', type=int, default=1, help='Počet dní zpět při --period days')
        parser.add_argument('--chunk-days', type=int, default=None, help='Kousky při --period days')
        parser.add_argument('--dry-run', action='store_true', help='Bez zápisu do DB')

    def handle(self, *args, **options):
        if options['fetch']:
            if not get_packeta_admin_for_fetch():
                raise CommandError(
                    'Chybí Packeta admin přihlašovací údaje v secrets (packeta_admin."0").'
                )
            self._handle_fetch(options)
            return

        if not options['csv']:
            raise CommandError(
                'Zadejte --csv <soubor> nebo --fetch --prodejna-id N [--period month]'
            )
        if not options['prodejna_id']:
            raise CommandError('--prodejna-id je povinné při importu z CSV')
        self._handle_csv(options)

    def _handle_fetch(self, options):
        period = options['period']
        typ_preset = options['typ']
        fetch_pid = options.get('prodejna_id')
        dry_run = options['dry_run']

        def on_progress(msg: str) -> None:
            self.stdout.write(msg)

        if period in ('month', 'yesterday'):
            if options.get('all_branches'):
                branches = []
                for pid in range(1, 7):
                    self.stdout.write(
                        f'Stahuji Packeta ({typ_preset}), období {period}, prodejna {pid}…'
                    )
                    try:
                        branch = fetch_and_import_branch(
                            pid,
                            period=period,
                            typ_preset=typ_preset,
                            dry_run=dry_run,
                            on_progress=on_progress,
                        )
                        branches.append(branch)
                    except RuntimeError as exc:
                        branches.append({
                            'prodejna_id': pid,
                            'branch_name': f'Prodejna {pid}',
                            'error': str(exc),
                        })
                result = {
                    'date_from': branches[0].get('date_from') if branches else None,
                    'date_to': branches[0].get('date_to') if branches else None,
                    'branches': branches,
                }
            elif not fetch_pid:
                raise CommandError(
                    f'--period {period} vyžaduje --prodejna-id nebo --all-branches.'
                )
            elif fetch_pid not in range(1, 7):
                raise CommandError('--prodejna-id musí být 1–6.')
            else:
                self.stdout.write(
                    f'Stahuji Packeta ({typ_preset}), období {period}, prodejna {fetch_pid}…'
                )
                try:
                    result = fetch_and_import_branch(
                        fetch_pid,
                        period=period,
                        typ_preset=typ_preset,
                        dry_run=dry_run,
                        on_progress=on_progress,
                    )
                except RuntimeError as exc:
                    raise CommandError(str(exc)) from exc
        else:
            if not options['all_branches']:
                raise CommandError('--period days vyžaduje --all-branches')
            days = max(1, options['days'] or 1)
            chunk_days = options['chunk_days'] or default_chunk_days(days)
            pid_note = f', jen prodejna {fetch_pid}' if fetch_pid else ''
            self.stdout.write(
                f'Stahuji Packeta, {days} dní, kousky po {chunk_days} dnech{pid_note}…'
            )
            try:
                result = fetch_and_import_all_branches(
                    days=days,
                    dry_run=dry_run,
                    chunk_days=chunk_days,
                    prodejna_id=fetch_pid,
                    on_progress=on_progress,
                )
            except RuntimeError as exc:
                raise CommandError(str(exc)) from exc

        suffix = ' [DRY RUN]' if dry_run else ''
        self.stdout.write(
            f'Období: {result["date_from"]} – {result["date_to"]}{suffix}'
        )
        self._print_branches(result['branches'])

    def _print_branches(self, branches):
        for branch in branches:
            name = branch['branch_name']
            pid = branch.get('prodejna_id')
            if branch.get('error'):
                self.stdout.write(self.style.ERROR(
                    f'  {name} (prodejna {pid}): CHYBA – {branch["error"]}'
                ))
            elif pid is None:
                self.stdout.write(self.style.WARNING(
                    f'  {name}: {branch.get("warning", "přeskočeno")}'
                ))
            else:
                stats = branch.get('stats') or {}
                self.stdout.write(self.style.SUCCESS(
                    f'  {name} (prodejna {pid}): řádků {branch.get("rows_total", 0)}, '
                    f'nových {branch.get("created", 0)}, přeskočeno {branch.get("skipped", 0)}'
                ))
                if stats:
                    self.stdout.write(
                        f'    Návštěvy: {stats.get("navstevy_celkem", 0)} '
                        f'(vydané {stats.get("vydane", 0)}, přijaté {stats.get("prijate", 0)})'
                    )
                if branch.get('warning'):
                    self.stdout.write(self.style.WARNING(f'    ⚠ {branch["warning"]}'))

    def _handle_csv(self, options):
        from django.utils import timezone

        prodejna_id = options['prodejna_id']
        if prodejna_id not in range(1, 7):
            raise CommandError('prodejna-id musí být 1–6.')

        csv_path = options['csv']
        try:
            with open(csv_path, 'rb') as f:
                content = f.read()
            rows = parse_packeta_csv(content)
        except OSError as exc:
            raise CommandError(f'Nelze přečíst soubor: {exc}') from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        dry_run = options['dry_run']
        batch = timezone.now().strftime('%Y%m%d%H%M%S')
        imp = import_packeta_rows(rows, prodejna_id, batch=batch, dry_run=dry_run)
        stats = imp['stats']
        suffix = ' [DRY RUN]' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'Prodejna {prodejna_id}: řádků {len(rows)}, nových {imp["created"]}, '
            f'přeskočeno {imp["skipped"]}{suffix}'
        ))
        self.stdout.write(
            f'Návštěvy (DISTINCT zásilka, hlavní typy): {stats["navstevy_celkem"]} '
            f'(vydané {stats["vydane"]}, přijaté {stats["prijate"]})'
        )
        if imp.get('warning'):
            self.stdout.write(self.style.WARNING(f'⚠ {imp["warning"]}'))
