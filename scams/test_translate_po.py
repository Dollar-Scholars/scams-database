import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from babel.messages.catalog import Catalog
from babel.messages.pofile import read_po, write_po
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from . import machine_translation
from .machine_translation import MACHINE_COMMENT, _finish, _protect


def make_po(locale_dir, code='es', locale='es'):
    catalog = Catalog(locale=locale)
    catalog.add('Report a scam')
    catalog.add('Already done', string='Ya hecho')
    catalog.add('%(count)s reports in %(period)s')
    catalog.add('See the <a href="%(url)s">dashboard</a>.')
    catalog.add(('%(count)s report', '%(count)s reports'), string=('', ''))
    path = Path(locale_dir) / locale / 'LC_MESSAGES' / 'django.po'
    path.parent.mkdir(parents=True)
    with path.open('wb') as file:
        write_po(file, catalog)
    return path


def load(path):
    with path.open('rb') as file:
        return {m.id: m for m in read_po(file) if m.id}


class TranslatePoTests(SimpleTestCase):
    def setUp(self):
        self.locale_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.locale_dir)
        self.po = make_po(self.locale_dir)

    def run_command(self, *args):
        out = StringIO()
        with override_settings(LOCALE_PATHS=[self.locale_dir]):
            call_command('translate_po', '-l', 'es', *args, stdout=out)
        return out.getvalue()

    def test_fills_only_untranslated_entries(self):
        self.run_command('--backend', 'dummy')
        messages = load(self.po)
        self.assertEqual(messages['Report a scam'].string, '[es] Report a scam')
        self.assertEqual(messages['Already done'].string, 'Ya hecho')  # left alone
        self.assertIn(MACHINE_COMMENT, messages['Report a scam'].auto_comments)
        self.assertNotIn(MACHINE_COMMENT, messages['Already done'].auto_comments)

    def test_placeholders_and_html_survive(self):
        self.run_command('--backend', 'dummy')
        messages = load(self.po)
        self.assertEqual(messages['%(count)s reports in %(period)s'].string,
                         '[es] %(count)s reports in %(period)s')
        self.assertEqual(messages['See the <a href="%(url)s">dashboard</a>.'].string,
                         '[es] See the <a href="%(url)s">dashboard</a>.')

    def test_plural_forms_are_all_filled(self):
        self.run_command('--backend', 'dummy')
        plural = load(self.po)[('%(count)s report', '%(count)s reports')]
        self.assertEqual(plural.string, ('[es] %(count)s report', '[es] %(count)s reports'))

    def test_a_translation_that_loses_a_placeholder_is_left_out(self):
        class Lossy:
            def translate(self, texts, target):
                return [text.replace('%(count)s', 'N') for text in texts]

        with mock.patch.dict(machine_translation.BACKENDS, {'lossy': Lossy}):
            out = self.run_command('--backend', 'lossy')
        messages = load(self.po)
        self.assertEqual(messages['%(count)s reports in %(period)s'].string, '')
        self.assertIn('skipped', out)

    def test_dry_run_counts_without_writing(self):
        before = self.po.read_bytes()
        out = self.run_command('--dry-run')
        self.assertEqual(self.po.read_bytes(), before)
        self.assertIn('es: 4 entries', out)

    def test_azure_without_a_key_explains_what_to_set(self):
        from django.core.management.base import CommandError
        with mock.patch.dict('os.environ', {'AZURE_TRANSLATOR_KEY': ''}):
            with self.assertRaisesMessage(CommandError, 'AZURE_TRANSLATOR_KEY'):
                self.run_command()


class ProtectionTests(SimpleTestCase):
    def test_placeholders_are_wrapped_but_not_inside_tags(self):
        text = 'See <a href="%(url)s">%(count)s reports</a>'
        self.assertEqual(
            _protect(text),
            'See <a href="%(url)s"><span class="notranslate">%(count)s</span> reports</a>')

    def test_finish_unwraps_and_unescapes_plain_text(self):
        self.assertEqual(_finish('Tom & Jerry %(n)s',
                                 'Tom &amp; Jerry <span class="notranslate">%(n)s</span>'),
                         'Tom & Jerry %(n)s')
