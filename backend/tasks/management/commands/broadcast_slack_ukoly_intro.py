"""Jednorázové představení Slack bota Úkoly všem aktivním uživatelům."""
from django.core.management.base import BaseCommand

from tasks.slack_notify import _app_base_url, send_slack_dm, slack_user_id_for_web_user
from users.models import WebUser

UKOLY_BOT_INTRO_MESSAGE = """Ahoj! 👋

V MOBILMAJAK teď funguje Slack bot *Úkoly* – posílá ti přehledné zprávy do soukromých zpráv ve Slacku (ne do kanálů).

*Co ti může chodit:*
• nový úkol ti někdo přiřadí
• ranní přehled úkolů *10 minut po začátku směny* (termíny, co hoří, poslední dokončení)
• blížící se nebo po termínu
• nový komentář u úkolu, který řešíš (vždy, když píše někdo jiný)
• dokončení, schválení – pokud úkoly zadáváš ty

*Kde to nastavit:*
Profil v MOBILMAJAK → Osobní údaje → *Slack – úkoly* (u adminů víc voleb pro dohled nad celou firmou).

*Důležité:*
E-mail v profilu MOBILMAJAK musí sedět se Slack účtem, jinak bot tě nenajde.

Odkaz: {app_url}/tasks/mine

Kdyby něco nechodilo nebo bylo moc, napiš Martinovi nebo Radkovi. Díky! 🙂"""


class Command(BaseCommand):
    help = "Pošle úvodní zprávu o Slack botovi Úkoly (výchozí dry-run)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--send",
            action="store_true",
            help="Skutečně odeslat (bez toho jen náhled)",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Jen jednomu uživateli (test)",
        )

    def handle(self, *args, **options):
        app_url = _app_base_url()
        text = UKOLY_BOT_INTRO_MESSAGE.format(app_url=app_url)

        self.stdout.write("=== Náhled zprávy ===\n")
        self.stdout.write(text)
        self.stdout.write("\n=== Konec náhledu ===\n")

        qs = WebUser.objects.filter(aktivni=True).order_by("prijmeni", "jmeno")
        if options["user_id"]:
            qs = qs.filter(pk=options["user_id"])

        if not options["send"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry-run – nic odesláno. Cíl: {qs.count()} aktivních uživatelů. "
                    "Pro odeslání přidej --send"
                )
            )
            return

        if not options["user_id"]:
            self.stdout.write(
                self.style.WARNING(
                    "Odesíláš všem aktivním uživatelům. Pro test použij --user-id ID --send"
                )
            )

        sent = 0
        skipped = 0
        for user in qs:
            slack_id = slack_user_id_for_web_user(user)
            if not slack_id:
                skipped += 1
                self.stdout.write(f"  SKIP #{user.id} {user.jmeno} {user.prijmeni} – bez Slacku")
                continue
            if send_slack_dm(slack_id, text):
                sent += 1
                self.stdout.write(f"  OK #{user.id} {user.jmeno} {user.prijmeni}")
            else:
                skipped += 1
                self.stdout.write(f"  FAIL #{user.id} {user.jmeno} {user.prijmeni}")

        self.stdout.write(self.style.SUCCESS(f"Odesláno: {sent}, přeskočeno: {skipped}"))
