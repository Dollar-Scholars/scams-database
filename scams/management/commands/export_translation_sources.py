"""
python manage.py export_translation_sources            # rewrite translation_sources.json
python manage.py export_translation_sources --check    # exit 1 if it is out of date

Writes ScamDB's English wording to translation_sources.json, the list dollarscholars.org
translates (scams/translation_sources.py, docs/TRANSLATIONS.md). Run it after changing
any wording, and commit the file with the change.
"""
from django.core.management.base import BaseCommand, CommandError

from scams.translation_sources import SOURCES_FILE, extract_all


class Command(BaseCommand):
    help = "Write ScamDB's English wording to translation_sources.json for dollarscholars.org."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true',
                            help='Only check that the file is up to date.')

    def handle(self, *args, check=False, **options):
        extraction = extract_all()
        for skipped in extraction.skipped:
            self.stderr.write(self.style.WARNING(skipped))
        if extraction.warnings:
            raise CommandError('Fix these first:\n' + '\n'.join(extraction.warnings))
        content = extraction.as_json()
        current = SOURCES_FILE.read_text(encoding='utf-8') if SOURCES_FILE.exists() else None
        name = SOURCES_FILE.name
        if check:
            if current != content:
                raise CommandError(f'{name} is out of date: run '
                                   'python manage.py export_translation_sources and commit it.')
            self.stdout.write(f'{name} is up to date ({len(extraction.messages)} texts).')
            return
        if current == content:
            self.stdout.write(f'{name} was already up to date ({len(extraction.messages)} texts).')
            return
        SOURCES_FILE.write_text(content, encoding='utf-8', newline='\n')
        self.stdout.write(self.style.SUCCESS(f'Wrote {name}: {len(extraction.messages)} texts.'))
