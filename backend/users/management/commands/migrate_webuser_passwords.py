from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import WebUser
from django.contrib.auth.hashers import check_password


def is_legacy_password(stored_password: str) -> bool:
    if not stored_password:
        return False
    if '$' in stored_password:
        return False
    if stored_password.startswith('pbkdf2_'):
        return False
    if stored_password.startswith('argon2'):
        return False
    if stored_password.startswith('bcrypt'):
        return False
    if stored_password.startswith('sha1$'):
        return False
    return True


class Command(BaseCommand):
    help = "Normalize WebUser records: rehash legacy plaintext passwords and trim usernames."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', default=False,
            help='Only print what would change, do not write to the database.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        total_users = 0
        legacy_passwords = 0
        rehashed = 0
        trimmed_usernames = 0
        unchanged = 0
        conflicts = []

        users = WebUser.objects.all().order_by('id')
        self.stdout.write(self.style.NOTICE(f"Scanning {users.count()} users..."))

        for user in users:
            total_users += 1
            changed = False

            # 1) Trim username whitespace (but keep original case to avoid unexpected changes)
            original_username = user.uzivatelske_jmeno
            trimmed_username = original_username.strip() if original_username else original_username
            if trimmed_username != original_username and trimmed_username:
                # Check for conflict
                exists_conflict = WebUser.objects.filter(uzivatelske_jmeno=trimmed_username).exclude(id=user.id).exists()
                if exists_conflict:
                    conflicts.append((user.id, original_username, trimmed_username))
                else:
                    if not dry_run:
                        user.uzivatelske_jmeno = trimmed_username
                    trimmed_usernames += 1
                    changed = True

            # 2) Rehash legacy plaintext passwords
            if is_legacy_password(user.heslo):
                legacy_passwords += 1
                if not dry_run:
                    # Use our model helper to safely hash and save
                    raw = user.heslo
                    user.set_heslo(raw)
                rehashed += 1
                changed = True

            if changed and not dry_run:
                # Persist minimal fields
                update_fields = ['uzivatelske_jmeno', 'heslo']
                # Keep only those actually changed
                to_update = []
                if user.uzivatelske_jmeno != original_username:
                    to_update.append('uzivatelske_jmeno')
                if is_legacy_password(user.heslo) is False and user.heslo != raw if 'raw' in locals() else False:
                    # Avoid evaluating previous line if raw not set; best-effort
                    pass
                # Always include heslo when we performed rehash
                if 'raw' in locals():
                    to_update.append('heslo')
                    del raw
                if to_update:
                    user.save(update_fields=to_update)
            if not changed:
                unchanged += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.write(self.style.SUCCESS(f"Total users: {total_users}"))
        self.stdout.write(self.style.SUCCESS(f"Legacy passwords found: {legacy_passwords}"))
        self.stdout.write(self.style.SUCCESS(f"Passwords rehashed: {rehashed}{' (dry-run)' if dry_run else ''}"))
        self.stdout.write(self.style.SUCCESS(f"Usernames trimmed: {trimmed_usernames}{' (dry-run)' if dry_run else ''}"))
        self.stdout.write(self.style.SUCCESS(f"Unchanged: {unchanged}"))

        if conflicts:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Username trim conflicts detected (id, original, trimmed):"))
            for c in conflicts:
                self.stdout.write(self.style.WARNING(f"- {c[0]}: '{c[1]}' -> '{c[2]}' (skipped)"))

