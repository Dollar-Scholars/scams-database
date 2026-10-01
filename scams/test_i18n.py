"""Tests for the translated site: every language's pages render, the page language and
direction, the hreflang alternates, and links to dollarscholars.org in the same language."""
import re

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation
from django.utils.translation import check_for_language

# Plain storage so {% static %} works in tests whether or not collectstatic has run
# (the test runner forces DEBUG=False, which makes manifest storages strict).
PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

PAGES = ('report_scam', 'dashboard', 'scam_awareness_page', 'thank_you', 'contributors')

# Django serves a /xx/ prefix only for a language it has a translation catalog for
# (check_for_language: its own conf/locale, or this project's locale/). Django ships none
# for these five, so until `locale/<code>/` exists for them their prefixed pages 404.
# Every other language in settings.LANGUAGES has a Django catalog and works today.
WITHOUT_CATALOG = {'am', 'ht', 'tl', 'yo', 'zu'}

RTL_LANGUAGES = {'ar', 'fa', 'he', 'ur'}

OUR_WORK = ('what-we-do/', 'core-curriculum/', 'resources/', 'blog/')


def url_in(code, name):
    with translation.override(code):
        return reverse(name)


def accepted_languages():
    return [code for code, _name in settings.LANGUAGES if check_for_language(code)]


class LanguageTestCase(TestCase):
    """A request to /es/... leaves Spanish active in this thread after the response
    (LocaleMiddleware activates it and nothing switches it back), which would leak into
    later tests; switch back to the default after each test."""

    def setUp(self):
        super().setUp()
        self.addCleanup(translation.deactivate)


def footer_html(response):
    html = response.content.decode()
    return html[html.index('<footer class="ds-footer">'):html.index('</footer>')]


@override_settings(STORAGES=PLAIN_STORAGES)
class EveryLanguageTests(LanguageTestCase):

    def test_only_languages_without_a_catalog_are_unavailable(self):
        unavailable = {code for code, _name in settings.LANGUAGES if not check_for_language(code)}
        self.assertLessEqual(unavailable, WITHOUT_CATALOG)

    def test_every_accepted_language_renders_every_page(self):
        for code in accepted_languages():
            for name in PAGES:
                url = url_in(code, name)
                with self.subTest(language=code, page=name, url=url):
                    if code != settings.LANGUAGE_CODE:
                        self.assertTrue(url.startswith(f'/{code}/'), url)
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    html = response.content.decode()
                    direction = 'rtl' if code in RTL_LANGUAGES else 'ltr'
                    self.assertIn(f'<html lang="{code}" dir="{direction}"', html)

    def test_languages_without_a_catalog_404_for_now(self):
        for code in sorted(WITHOUT_CATALOG - set(accepted_languages())):
            with self.subTest(language=code):
                self.assertEqual(self.client.get(f'/{code}/dashboard/').status_code, 404)


@override_settings(STORAGES=PLAIN_STORAGES)
class PageLanguageTests(LanguageTestCase):

    def test_arabic_is_right_to_left(self):
        response = self.client.get('/ar/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<html lang="ar" dir="rtl"')

    def test_english_is_left_to_right_and_unprefixed(self):
        self.assertEqual(reverse('dashboard'), '/dashboard/')
        self.assertContains(self.client.get('/dashboard/'), '<html lang="en" dir="ltr"')

    def test_hreflang_alternates(self):
        response = self.client.get('/es/dashboard/')
        self.assertContains(response, '<link rel="alternate" hreflang="en" href="http://testserver/dashboard/">')
        self.assertContains(response, '<link rel="alternate" hreflang="es" href="http://testserver/es/dashboard/">')
        self.assertContains(response, '<link rel="alternate" hreflang="ar" href="http://testserver/ar/dashboard/">')

    def test_app_links_keep_the_language(self):
        html = self.client.get('/es/dashboard/').content.decode()
        for name in ('report_scam', 'scam_awareness_page', 'contributors'):
            self.assertIn(f'href="{url_in("es", name)}"', html)


@override_settings(STORAGES=PLAIN_STORAGES)
class MainSiteLinksInPageLanguageTests(LanguageTestCase):
    """The fallback header and footer link to dollarscholars.org in the page's language."""

    def test_spanish_pages_link_to_the_spanish_main_site(self):
        response = self.client.get('/es/dashboard/')
        footer = footer_html(response)
        for path in OUR_WORK:
            self.assertIn(f'href="https://dollarscholars.org/es/{path}"', footer)
        self.assertIn('href="https://dollarscholars.org/es/privacy-policy/"', footer)
        self.assertIn('href="https://dollarscholars.org/es/accessibility-statement/"', footer)
        self.assertIn('href="https://dollarscholars.org/es/" class="footer-brand"', footer)
        self.assertNotRegex(footer, r'href="https://dollarscholars\.org/(?!es/)')
        self.assertContains(response, '<a class="brand" href="https://dollarscholars.org/es/"')

    def test_english_pages_link_to_unprefixed_main_site(self):
        response = self.client.get('/dashboard/')
        footer = footer_html(response)
        for path in OUR_WORK:
            self.assertIn(f'href="https://dollarscholars.org/{path}"', footer)
        self.assertNotRegex(footer, r'href="https://dollarscholars\.org/[a-z]{2}(-[a-z]+)?/')
        self.assertContains(response, '<a class="brand" href="https://dollarscholars.org/"')

    def test_chinese_uses_the_main_sites_code(self):
        footer = footer_html(self.client.get('/zh-hans/dashboard/'))
        self.assertIn('href="https://dollarscholars.org/zh-hans/what-we-do/"', footer)

    def test_links_off_the_main_site_are_unchanged(self):
        footer = footer_html(self.client.get('/es/dashboard/'))
        self.assertIn('href="mailto:partnerships@dollarscholars.org"', footer)
        self.assertIn('href="https://www.paypal.com/donate/?hosted_button_id=QUDB8VUWZX5RQ"', footer)
        self.assertIn('href="https://github.com/Dollar-Scholars"', footer)


@override_settings(STORAGES=PLAIN_STORAGES)
class ThemeToggleLabelsTests(LanguageTestCase):
    """theme-toggle.js has no text of its own: its labels come from the template."""

    def test_labels_rendered_for_the_script(self):
        html = self.client.get('/es/dashboard/').content.decode()
        self.assertRegex(html, r'data-label-light="[^"]+"\s+data-label-dark="[^"]+"')

    def test_scripts_have_no_english_labels(self):
        from django.contrib.staticfiles import finders
        for asset in ('scams/js/theme-toggle.js', 'scams/js/site-nav.js'):
            with self.subTest(asset=asset):
                with open(finders.find(asset), encoding='utf-8') as f:
                    code = re.sub(r'/\*.*?\*/|//[^\n]*', '', f.read(), flags=re.S)
                for label in ('Switch to', 'Menu', 'Open menu', 'Close menu'):
                    self.assertNotIn(label, code)
