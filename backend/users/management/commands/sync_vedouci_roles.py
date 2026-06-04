from django.core.management.base import BaseCommand

from users.vedouci_utils import sync_vedouci_roles_from_stores


class Command(BaseCommand):
    help = "Nastaví roli VEDOUCI u uživatelů přiřazených jako vedoucí pobočky (Prodejna.vedouci_user_id)."

    def handle(self, *args, **options):
        n = sync_vedouci_roles_from_stores()
        self.stdout.write(self.style.SUCCESS(f"Upraveno uživatelů: {n}"))
