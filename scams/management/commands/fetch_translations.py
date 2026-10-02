"""
python manage.py fetch_translations

Downloads ScamDB's translations from dollarscholars.org (DS_TRANSLATIONS_URL), where they
are made and reviewed, and writes locale/<language>/LC_MESSAGES/django.mo, the files Django
reads. The container runs this when it starts (Dockerfile), so restarting ScamDB brings in
the latest translations.

If the download fails, the files already there are kept and the command still succeeds, so
ScamDB starts anyway (in English wherever it has no translation). --strict fails instead.
"""
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import to_locale

from scams.languages import TARGET_LANGUAGES

FORMAT_VERSION = 1
# Placeholders a translation must keep: %(name)s, and %% for a literal % in
# {% blocktranslate %}. One that lost or mangled one would break the page.
PLACEHOLDER_RE = re.compile(r'%\(\w+\)[sdif]|%%')


class FetchError(Exception):
    pass


def download(url, timeout):
    request = urllib.request.Request(url, headers={'User-Agent': 'scamdb.dollarscholars.org'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, OSError) as exc:
        raise FetchError(f"couldn't download {url}: {exc}")
    except ValueError as exc:
        raise FetchError(f'{url} did not return JSON: {exc}')
    if not isinstance(data, dict) or data.get('version') != FORMAT_VERSION \
            or not isinstance(data.get('messages'), list):
        raise FetchError(f'{url}: not the expected format (version {FORMAT_VERSION})')
    return data['messages']


def build_catalogs(messages):
    """{language: babel Catalog} for every target language, and how many translations were
    left out because their placeholders don't match the English."""
    catalogs = {code: Catalog(locale=None, domain='django', fuzzy=False)
                for code in TARGET_LANGUAGES}
    left_out = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        text, context = message.get('text'), message.get('context') or None
        translations = message.get('translations')
        if not isinstance(text, str) or not isinstance(translations, dict):
            continue
        expected = Counter(PLACEHOLDER_RE.findall(text))
        for code, translated in translations.items():
            if code not in catalogs or not isinstance(translated, str) or not translated:
                continue
            if Counter(PLACEHOLDER_RE.findall(translated)) != expected:
                left_out += 1
                continue
            catalogs[code].add(text, string=translated, context=context)
    return catalogs, left_out


def write_catalog(catalog, path):
    """Write the .mo file in one step, so a running server never reads half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix='.mo.tmp')
    try:
        with os.fdopen(handle, 'wb') as file:
            write_mo(file, catalog)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class Command(BaseCommand):
    help = "Download ScamDB's translations from dollarscholars.org and write the .mo files."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--url', help='Default: DS_TRANSLATIONS_URL.')
        parser.add_argument('--timeout', type=float, default=30, help='Seconds (default 30).')
        parser.add_argument('--strict', action='store_true',
                            help='Fail if the download fails, instead of keeping the old files.')

    def handle(self, *args, url=None, timeout=30, strict=False, **options):
        url = url or settings.DS_TRANSLATIONS_URL
        if not url:
            self.stdout.write('DS_TRANSLATIONS_URL is empty: translations not downloaded.')
            return
        try:
            messages = download(url, timeout)
        except FetchError as exc:
            if strict:
                raise CommandError(str(exc))
            self.stderr.write(self.style.WARNING(
                f'Translations not updated, the ones already here are kept: {exc}'))
            return
        catalogs, left_out = build_catalogs(messages)
        locale_dir = Path(settings.LOCALE_PATHS[0])
        for code, catalog in catalogs.items():
            write_catalog(catalog, locale_dir / to_locale(code) / 'LC_MESSAGES' / 'django.mo')
        total = sum(len(catalog) for catalog in catalogs.values())
        note = (f'; {left_out} left out because their placeholders do not match the English'
                if left_out else '')
        self.stdout.write(self.style.SUCCESS(
            f'Translations: {total} in {len(catalogs)} languages{note}.'))
