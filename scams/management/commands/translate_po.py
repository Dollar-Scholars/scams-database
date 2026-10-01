"""Fill locale/<lang>/LC_MESSAGES/django.po by machine translation (Azure Translator).

    python manage.py makemessages --all --no-obsolete      # collect new English text
    python manage.py translate_po --dry-run                 # what would be sent, in characters
    python manage.py translate_po                           # every language
    python manage.py translate_po -l es -l fr               # some languages
    python manage.py compilemessages

Only entries without a translation are sent, so reviewed or corrected translations are
never replaced. Needs AZURE_TRANSLATOR_KEY / AZURE_TRANSLATOR_REGION (see .env.example).
"""
from pathlib import Path

from babel.messages.pofile import read_po, write_po
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from scams.machine_translation import MachineTranslationError, fill_catalog, get_backend, pending


class Command(BaseCommand):
    help = "Machine-translate the untranslated entries of the .po catalogs (Azure Translator)."

    def add_arguments(self, parser):
        parser.add_argument("-l", "--language", action="append", dest="languages",
                            help="Language code (repeatable). Default: every language but English.")
        parser.add_argument("--backend", default="azure", help="azure (default) or dummy.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Only count the entries and characters that would be sent.")

    def handle(self, *args, languages=None, backend="azure", dry_run=False, **options):
        known = [code for code, _name in settings.LANGUAGES if code != settings.LANGUAGE_CODE]
        languages = languages or known
        unknown = sorted(set(languages) - set(known))
        if unknown:
            raise CommandError(f"Unknown language(s): {', '.join(unknown)}")
        locale_dir = Path(settings.LOCALE_PATHS[0])
        engine = None if dry_run else self._backend(backend)

        total_entries = total_chars = 0
        for code in languages:
            path = locale_dir / self._locale(code) / "LC_MESSAGES" / "django.po"
            if not path.exists():
                raise CommandError(f"{path} does not exist. Run makemessages first.")
            with path.open("rb") as file:
                catalog = read_po(file, locale=None)
            if dry_run:
                todo = list(pending(catalog))
                chars = sum(len(text) for text in dict.fromkeys(t for _m, ts in todo for t in ts))
                self.stdout.write(f"{code}: {len(todo)} entries, {chars} characters")
                total_entries += len(todo)
                total_chars += chars
                continue
            try:
                done, chars, skipped = fill_catalog(catalog, code, engine)
            except MachineTranslationError as exc:
                raise CommandError(f"{code}: {exc}")
            with path.open("wb") as file:
                write_po(file, catalog, width=79)
            total_entries += done
            total_chars += chars
            note = f", {skipped} skipped (lost a placeholder; left untranslated)" if skipped else ""
            self.stdout.write(f"{code}: {done} entries translated, {chars} characters{note}")
        verb = "would send" if dry_run else "sent"
        self.stdout.write(self.style.SUCCESS(
            f"{len(languages)} language(s): {total_entries} entries, {verb} {total_chars} characters"))

    def _backend(self, name):
        try:
            return get_backend(name)
        except MachineTranslationError as exc:
            raise CommandError(str(exc))

    @staticmethod
    def _locale(code):
        # Django's directory names: es-mx -> es_MX, zh-hans -> zh_Hans.
        from django.utils.translation import to_locale
        return to_locale(code)
