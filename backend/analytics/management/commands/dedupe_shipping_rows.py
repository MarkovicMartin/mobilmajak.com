from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q, Min, Count
from analytics.models import WebProdejeAll


class Command(BaseCommand):
    help = (
        "Najde a případně odstraní duplicitní speciální řádky: dopravy (Zásilkovna/Balíkovna/Osobní odběr/varianty, Česká pošta, Allegro doručení)\n"
        "a také duplicitní položky s názvem \"Zaokrouhlení\".\n"
        "Duplicitou se rozumí více než 1 výskyt na stejném dokladu (klíč: doklad+pokladna+typ+id_prodejny); vždy ponechá nejstarší záznam."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Provést mazání (bez tohoto flagu jen vypíše statistiku)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Volitelně omezí počet zpracovaných skupin duplicit (pro bezpečné dávky)",
        )

    def handle(self, *args, **options):
        apply = options.get("apply", False)
        limit = options.get("limit")

        # Klíčová slova pro dopravu / výdej
        shipping_keywords = [
            # Zásilkovna / Zásielkovňa
            "Zásilkovna", "Zasilkovna", "ZÁSILKOVNA",
            "Zásielkovňa", "Zasielkovna", "ZÁSIELKOVŇA",
            # Balíkovna
            "Balíkovna", "Balikovna", "BALÍKOVNA",
            # Osobní odběr
            "Osobní odběr", "Osobni odber", "OSOBNÍ ODBĚR", "OSOBNI ODBER",
            # Česká pošta
            "Česká Pošta", "Česká pošta", "Ceska posta", "ČESKÁ POŠTA",
            # Česká pošta – specifická varianta s kartou/GP/Apple Pay
            "Česká Pošta - Balík Do Ruky - Online platební kartou / Google pay / Apple pay",
            "Ceska Posta - Balik Do Ruky - Online platebni kartou / Google pay / Apple pay",
            # Allegro doručení
            "Allegro doručení", "Allegro doruceni",
            # Allegro – specifická varianta s kartou/GP/Apple Pay
            "Allegro doručení - Online platební kartou / Google pay / Apple pay",
            "Allegro doruceni - Online platebni kartou / Google pay / Apple pay",
        ]

        # Klíčová slova pro zaokrouhlení (různé zápisy bez/ s diakritikou)
        rounding_keywords = [
            "Zaokrouhlení", "Zaokrouhleni", "ZAOKROUHLENÍ", "ZAOKROUHLENI",
        ]

        # Filtrovat pouze relevantní názvy a doklady s vyplněnými identifikátory
        name_q = Q()
        for kw in shipping_keywords:
            name_q |= Q(nazev__icontains=kw)
        for kw in rounding_keywords:
            name_q |= Q(nazev__icontains=kw)

        base = WebProdejeAll.objects.exclude(doklad__isnull=True).exclude(doklad='')
        shipping_qs = base.filter(
            Q(
                # any of shipping keywords
                **{}
            )
        )
        # Django Q composition above with **{} is a placeholder to keep style; we already built name_q that includes both shipping and rounding.
        # Rozdělíme explicitně na dvě množiny:
        shipping_only_q = Q()
        for kw in shipping_keywords:
            shipping_only_q |= Q(nazev__icontains=kw)
        rounding_only_q = Q()
        for kw in rounding_keywords:
            rounding_only_q |= Q(nazev__icontains=kw)

        shipping_qs = base.filter(shipping_only_q)
        rounding_qs = base.filter(rounding_only_q)

        # Najít skupiny, kde je víc než 1 výskyt na stejném dokladu (robustní klíč)
        def find_dupes(qs, label):
            groups = (
                qs
                .values("doklad", "pokladna", "typ", "id_prodejny")
                .annotate(cnt=Count("id"), min_id=Min("id"))
                .filter(cnt__gt=1)
                .order_by()
            )
            total = groups.count()
            if limit is not None:
                groups = groups[:limit]
            ids, inspected = [], 0
            for g in groups:
                group_q = qs.filter(
                    doklad=g["doklad"],
                    pokladna=g["pokladna"],
                    typ=g["typ"],
                    id_prodejny=g["id_prodejny"],
                ).order_by("id")
                inspected += group_q.count()
                keep_id = g["min_id"]
                for _id in group_q.values_list("id", flat=True):
                    if _id != keep_id:
                        ids.append(_id)
            self.stdout.write(self.style.NOTICE(f"[{label}] skupin: {total} | k mazání: {len(ids)}"))
            return ids, inspected, total

        ids_to_delete = []
        inspected_rows = 0
        total_groups = 0
        ids_ship, inspected_ship, groups_ship = find_dupes(shipping_qs, "Doprava")
        ids_round, inspected_round, groups_round = find_dupes(rounding_qs, "Zaokrouhlení")
        ids_to_delete.extend(ids_ship)
        ids_to_delete.extend(ids_round)
        inspected_rows = inspected_ship + inspected_round
        total_groups = groups_ship + groups_round

        self.stdout.write(self.style.NOTICE(
            f"Celkem skupin: {total_groups} | Celkem k mazání: {len(ids_to_delete)} | Zkontrolováno řádků: {inspected_rows}"
        ))

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run: nic se nemaže. Přidej --apply pro provedení."))
            return

        if not ids_to_delete:
            self.stdout.write(self.style.SUCCESS("Žádné duplicity k mazání."))
            return

        # Provedeme mazání v jedné transakci
        with transaction.atomic():
            deleted, _ = WebProdejeAll.objects.filter(id__in=ids_to_delete).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Smazáno duplicitních řádků: {deleted}. (Skupin: {total_groups}, prohlédnutých řádků: {inspected_rows})"
            )
        )


