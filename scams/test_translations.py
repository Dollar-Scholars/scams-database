"""ScamDB's wording goes to dollarscholars.org to be translated (translation_sources.json),
and the translations come back with `python manage.py fetch_translations`."""
import gettext
import json
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import translation
from django.utils.translation import trans_real

from .test_i18n import PLAIN_STORAGES
from .translation_sources import Extraction, extract_all, extract_python

URL = 'https://dollarscholars.example/translations/scamdb.json'


class SourcesTests(SimpleTestCase):

    def test_the_committed_list_is_up_to_date(self):
        # Fails after a wording change: run `python manage.py export_translation_sources`
        # and commit translation_sources.json with the change.
        call_command('export_translation_sources', '--check', stdout=StringIO(),
                     stderr=StringIO())

    def test_all_wording_can_be_collected(self):
        self.assertEqual(extract_all().warnings, [])

    def test_the_list_has_the_pages_wording(self):
        data = json.loads(extract_all().as_json())
        texts = {m['text']: m for m in data['messages']}
        self.assertEqual(data['version'], 1)
        self.assertIn('Scams by date occurred', texts)
        summary = texts['Reports: %(count)s']
        self.assertTrue(summary['is_format'])
        self.assertEqual([place.split(':')[0] for place in summary['locations']],
                         ['scams/views.py'])

    def test_a_word_between_two_placeholders_is_refused(self):
        extraction = Extraction()
        extraction.add('%(first)s to %(last)s', '', True, 'views.py:1')
        extraction.add('%(code)s — %(name)s', '', True, 'views.py:2')
        self.assertEqual(len(extraction.warnings), 1)
        self.assertIn('views.py:1', extraction.warnings[0])

    def test_plurals_are_refused(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        path = folder / 'views.py'
        path.write_text("ngettext('%(n)s report', '%(n)s reports', n)\n_('Hello')\n",
                        encoding='utf-8')
        extraction = Extraction()
        with mock.patch('scams.translation_sources._relative', return_value='views.py'):
            extract_python(path, extraction)
        self.assertEqual(extraction.warnings,
                         ['views.py:1: ngettext() is not supported; reword without a plural'])
        self.assertEqual(list(extraction.messages), [('', 'Hello')])


def fake_response(payload):
    response = mock.MagicMock()
    response.read.return_value = json.dumps(payload).encode('utf-8')
    response.__enter__.return_value = response
    return response


DOWNLOAD = {'version': 1, 'messages': [
    {'text': 'Scam dashboard', 'context': '',
     'translations': {'es': 'Panel de estafas', 'fr': 'Tableau des arnaques'}},
    {'text': 'Reports: %(count)s', 'context': '',
     'translations': {'es': 'Denuncias: %(count)s', 'de': 'Meldungen: %(anzahl)s'}},
    {'text': 'May', 'context': 'month', 'translations': {'es': 'Mayo', 'xx': 'unknown'}},
]}


class FetchTests(SimpleTestCase):

    def setUp(self):
        self.locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.locale_dir)
        settings = override_settings(LOCALE_PATHS=[self.locale_dir], DS_TRANSLATIONS_URL=URL)
        settings.enable()
        self.addCleanup(settings.disable)

    def fetch(self, *args, payload=DOWNLOAD, error=None):
        out, err = StringIO(), StringIO()
        side_effect = error or (lambda request, timeout: fake_response(payload))
        with mock.patch('urllib.request.urlopen', side_effect=side_effect) as urlopen:
            call_command('fetch_translations', *args, stdout=out, stderr=err)
        self.requests = urlopen.call_args_list
        return out.getvalue(), err.getvalue()

    def catalog(self, folder):
        with (self.locale_dir / folder / 'LC_MESSAGES' / 'django.mo').open('rb') as file:
            return gettext.GNUTranslations(file)

    def test_writes_a_catalog_per_language(self):
        out, _err = self.fetch()
        self.assertEqual(self.requests[0].args[0].full_url, URL)
        spanish = self.catalog('es')
        self.assertEqual(spanish.gettext('Scam dashboard'), 'Panel de estafas')
        self.assertEqual(spanish.gettext('Reports: %(count)s'), 'Denuncias: %(count)s')
        self.assertEqual(spanish.pgettext('month', 'May'), 'Mayo')
        self.assertEqual(self.catalog('fr').gettext('Scam dashboard'), 'Tableau des arnaques')
        # Every language gets a catalog, so Django serves its pages, translated or not.
        self.assertEqual(self.catalog('zh_Hans').gettext('Scam dashboard'),
                         'Scam dashboard')
        self.assertTrue((self.locale_dir / 'am' / 'LC_MESSAGES' / 'django.mo').exists())
        self.assertIn('Translations: 4 in 43 languages; 1 left out', out)

    def test_a_translation_that_lost_a_placeholder_is_left_out(self):
        self.fetch()
        self.assertEqual(self.catalog('de').gettext('Reports: %(count)s'), 'Reports: %(count)s')

    def test_a_failed_download_keeps_the_old_catalogs(self):
        self.fetch()
        _out, err = self.fetch(error=OSError('connection refused'))
        self.assertIn('Translations not updated', err)
        self.assertEqual(self.catalog('es').gettext('Scam dashboard'), 'Panel de estafas')

    def test_strict_fails_on_a_failed_download(self):
        with self.assertRaisesMessage(CommandError, 'connection refused'):
            self.fetch('--strict', error=OSError('connection refused'))

    def test_something_other_than_the_catalog_is_refused(self):
        with self.assertRaisesMessage(CommandError, 'not the expected format'):
            self.fetch('--strict', payload={'detail': 'Not found'})
        self.assertFalse((self.locale_dir / 'es').exists())

    def test_no_url_no_download(self):
        with override_settings(DS_TRANSLATIONS_URL=''):
            out, _err = self.fetch()
        self.assertEqual(self.requests, [])
        self.assertIn('not downloaded', out)


@override_settings(STORAGES=PLAIN_STORAGES)
class TranslatedPageTests(TestCase):

    def setUp(self):
        locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, locale_dir)
        settings = override_settings(LOCALE_PATHS=[locale_dir], DS_TRANSLATIONS_URL=URL)
        settings.enable()
        self.addCleanup(settings.disable)
        self.addCleanup(self.forget_catalogs)
        self.addCleanup(translation.deactivate)
        with mock.patch('urllib.request.urlopen', return_value=fake_response(DOWNLOAD)):
            call_command('fetch_translations', stdout=StringIO())
        self.forget_catalogs()

    @staticmethod
    def forget_catalogs():
        trans_real._translations = {}
        trans_real._default = None

    def test_the_page_shows_the_downloaded_translation(self):
        self.assertContains(self.client.get('/es/dashboard/'), 'Panel de estafas')
        self.assertContains(self.client.get('/dashboard/'), 'Scam dashboard')
