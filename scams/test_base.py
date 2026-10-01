"""Tests for the shared Dollar Scholars page chrome: scams/templates/scams/base.html,
its partials, and the static files it references."""
import re

from django import forms
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.staticfiles import finders
from django.template import engines
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

# Plain storage so {% static %} works in tests whether or not collectstatic has run
# (the test runner forces DEBUG=False, which makes manifest storages strict).
PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

CHILD_TEMPLATE = (
    '{% extends "scams/base.html" %}'
    '{% block title %}Probe page{% endblock %}'
    '{% block meta_description %}Probe description{% endblock %}'
    '{% block extra_head %}<meta name="probe-head" content="1">{% endblock %}'
    '{% block content %}<p id="probe-content">Hello from the content block</p>{% endblock %}'
    '{% block extra_js %}<script id="probe-js"></script>{% endblock %}'
)

STATIC_ASSETS = [
    'scams/css/ds-theme.css',
    'scams/js/theme-toggle.js',
    'scams/js/site-nav.js',
    'scams/img/vector_logo_ds_small.svg',
    'scams/img/vector_logo_ds_small_white.svg',
]

APP_NAV = [
    ('report_scam', 'Report a scam'),
    ('dashboard', 'Dashboard'),
    ('scam_awareness_page', 'Scam awareness'),
]


def make_request(path='/', message_list=()):
    request = RequestFactory().get(path)
    request.resolver_match = resolve(path)
    request.session = {}
    request._messages = FallbackStorage(request)
    for level, text in message_list:
        messages.add_message(request, level, text)
    return request


def render_child(path='/', message_list=()):
    return engines['django'].from_string(CHILD_TEMPLATE).render({}, make_request(path, message_list))


def nav_block(html):
    """The <nav aria-label="Main"> element of the header."""
    match = re.search(r'<nav class="site-nav" aria-label="Main">(.*?)</nav>', html, re.S)
    assert match, 'header nav not found'
    return match.group(1)


@override_settings(STORAGES=PLAIN_STORAGES)
class BaseTemplateTests(SimpleTestCase):

    def test_blocks_render_in_place(self):
        html = render_child()
        self.assertIn('<title>Probe page | Dollar Scholars</title>', html)
        self.assertIn('<meta name="description" content="Probe description">', html)
        self.assertIn('<meta name="probe-head" content="1">', html)
        head, body = html.split('</head>', 1)
        self.assertIn('probe-head', head)
        main = re.search(r'<main id="main-content"[^>]*>(.*?)</main>', body, re.S)
        self.assertIsNotNone(main)
        self.assertIn('id="probe-content"', main.group(1))
        # extra_js comes after the footer, at the end of <body>
        self.assertLess(body.index('</footer>'), body.index('id="probe-js"'))

    def test_default_title_and_description(self):
        html = engines['django'].from_string('{% extends "scams/base.html" %}').render({}, make_request())
        self.assertIn('<title>Scam Reports | Dollar Scholars</title>', html)
        self.assertRegex(html, r'<meta name="description" content="[^"]+">')

    def test_theme_init_script_runs_before_css(self):
        html = render_child()
        self.assertIn('<html lang="en" dir="ltr" class="no-js">', html)
        init = html.index("localStorage.getItem('ds.website.theme')")
        self.assertLess(init, html.index('rel="stylesheet"'))
        self.assertIn("prefers-color-scheme: dark", html[:html.index('rel="stylesheet"')])
        self.assertIn('root.dataset.theme = theme', html)
        self.assertIn('root.style.colorScheme = theme', html)

    def test_skip_link_and_landmarks(self):
        html = render_child()
        self.assertInHTML('<a href="#main-content" class="skip-link">Skip to main content</a>', html)
        self.assertIn('<header class="site-header">', html)
        self.assertIn('<main id="main-content" class="site-main" tabindex="-1">', html)
        self.assertIn('<footer class="ds-footer">', html)
        self.assertLess(html.index('skip-link'), html.index('<header class="site-header">'))

    def test_header_brand_and_product_label(self):
        html = render_child()
        self.assertIn('<a class="brand" href="https://dollarscholars.org/" aria-label="Dollar Scholars Foundation home">', html)
        self.assertIn('Dollar Scholars<span class="brand-title-extra"> Foundation</span>', html)
        self.assertInHTML(f'<a class="product-label" href="{reverse("report_scam")}">Scam Reports</a>', html)
        self.assertIn(f'src="{static("scams/img/vector_logo_ds_small.svg")}" alt="" class="ds-logo-light"', html)
        self.assertIn(f'src="{static("scams/img/vector_logo_ds_small_white.svg")}" alt="" class="ds-logo-dark"', html)

    def test_nav_links_use_app_urls(self):
        nav = nav_block(render_child('/scam-awareness/'))
        for url_name, label in APP_NAV:
            self.assertRegex(nav, rf'<a href="{re.escape(reverse(url_name))}"[^>]*>{label}</a>')
        self.assertNotIn('/all-scams/', nav)

    def test_active_nav_item_marked_with_aria_current(self):
        for url_name, label in APP_NAV:
            with self.subTest(url_name=url_name):
                nav = nav_block(render_child(reverse(url_name)))
                self.assertEqual(nav.count('aria-current'), 1)
                self.assertIn(f'<a href="{reverse(url_name)}" aria-current="page">{label}</a>', nav)

    def test_thank_you_marks_report_section_not_page(self):
        nav = nav_block(render_child(reverse('thank_you')))
        self.assertIn(f'<a href="{reverse("report_scam")}" aria-current="true">Report a scam</a>', nav)
        self.assertNotIn('aria-current="page"', nav)

    def test_header_cta_and_hamburger(self):
        html = render_child()
        self.assertInHTML(
            f'<a class="btn btn-primary header-cta" href="{reverse("report_scam")}">Report a scam</a>', html)
        self.assertRegex(
            html, r'<button id="site-nav-toggle" class="nav-toggle" type="button"\s+'
                  r'aria-expanded="false" aria-controls="site-nav-panel" aria-label="Menu">')
        self.assertIn('<div id="site-nav-panel" class="site-nav-panel">', html)

    def test_theme_toggle_matches_site_markup(self):
        html = render_child()
        self.assertRegex(
            html,
            r'<button id="ds-theme-toggle" class="ds-theme-toggle" type="button"\s+'
            r'data-label-light="Switch to light mode"\s+'
            r'data-label-dark="Switch to dark mode" aria-label="Switch to dark mode"\s+'
            r'title="Switch to dark mode">')
        self.assertIn('class="ds-theme-moon"', html)
        self.assertIn('class="ds-theme-sun"', html)

    def test_footer_columns_and_links(self):
        html = render_child()
        footer = html[html.index('<footer class="ds-footer">'):html.index('</footer>')]
        for heading in ('Scam Reports', 'Our Work', 'Help &amp; Policies'):
            self.assertIn(f'>{heading}</h2>', footer)
        for url_name, label in APP_NAV:
            self.assertInHTML(f'<a href="{reverse(url_name)}">{label}</a>', footer)
        self.assertNotIn('/all-scams/', footer)
        for href in (
            'https://dollarscholars.org/',
            'https://dollarscholars.org/what-we-do/',
            'https://dollarscholars.org/core-curriculum/',
            'https://dollarscholars.org/resources/',
            'https://dollarscholars.org/blog/',
            'https://dollarscholars.org/privacy-policy/',
            'https://dollarscholars.org/accessibility-statement/',
            'mailto:partnerships@dollarscholars.org',
            'https://www.paypal.com/donate/?hosted_button_id=QUDB8VUWZX5RQ',
            'https://www.linkedin.com/company/dollarscholars/',
            'https://github.com/Dollar-Scholars',
        ):
            self.assertIn(f'href="{href}"', footer)
        self.assertIn('Growing the economy through adult financial education.', footer)
        year = timezone.localdate().year
        self.assertIn(f'&copy; {year} <span translate="no">Dollar Scholars Foundation</span>. All rights reserved.', footer)
        self.assertIn('aria-label="LinkedIn"', footer)
        self.assertIn('aria-label="GitHub"', footer)

    def test_no_messages_slot_without_messages(self):
        self.assertNotIn('class="messages', render_child())

    def test_messages_render_as_alerts(self):
        html = render_child(message_list=[
            (messages.SUCCESS, 'Report saved.'),
            (messages.ERROR, 'Something went wrong.'),
        ])
        self.assertIn('<section class="messages container" aria-label="Notifications">', html)
        self.assertRegex(html, r'class="alert alert-success"\s+role="status">\s*<div class="alert-body">Report saved.</div>')
        self.assertRegex(html, r'class="alert alert-error"\s+role="alert">\s*<div class="alert-body">Something went wrong.</div>')
        main = html[html.index('<main id="main-content"'):html.index('</main>')]
        self.assertLess(main.index('class="messages'), main.index('id="probe-content"'))

    def test_static_assets_linked(self):
        html = render_child()
        self.assertIn(f'<link rel="icon" type="image/svg+xml" href="{static("scams/img/vector_logo_ds_small.svg")}">', html)
        self.assertIn(f'<link rel="stylesheet" href="{static("scams/css/ds-theme.css")}">', html)
        self.assertIn(f'<script src="{static("scams/js/theme-toggle.js")}" defer></script>', html)
        self.assertIn(f'<script src="{static("scams/js/site-nav.js")}" defer></script>', html)
        self.assertIn(f'src="{static("scams/img/vector_logo_ds_small_white.svg")}" alt="" width="32" height="32"', html)

    def test_every_referenced_static_file_exists(self):
        for asset in STATIC_ASSETS:
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset), f'{asset} not found by staticfiles finders')

        prefix = static('')
        html = render_child()
        referenced = set(re.findall(r'(?:href|src)="' + re.escape(prefix) + r'([^"?#]+)', html))
        self.assertEqual(referenced, set(STATIC_ASSETS))
        for path in referenced:
            with self.subTest(path=path):
                self.assertIsNotNone(finders.find(path), f'{path} referenced by base.html but not found')


class DemoForm(forms.Form):
    title = forms.CharField(label='Title')
    contact_method = forms.ChoiceField(
        label='How were you contacted?', choices=[('sms', 'SMS'), ('email', 'Email')],
        widget=forms.RadioSelect(attrs={'id': 'contactMethod'}))
    anonymous = forms.BooleanField(label='Submit anonymously', required=False)


class FormFieldPartialTests(SimpleTestCase):

    def render_field(self, form, name, **extra):
        return render_to_string('scams/partials/form_field.html', {'field': form[name], **extra})

    def test_text_field_with_error(self):
        form = DemoForm(data={'title': '', 'contact_method': 'sms'})
        form.is_valid()
        html = self.render_field(form, 'title', extra_class='field-full')
        self.assertIn('<div class="field has-error field-full">', html)
        self.assertIn('<label for="id_title">Title<span class="req" aria-hidden="true">*</span></label>', html)
        self.assertIn('name="title"', html)
        self.assertIn('<ul class="errorlist" id="id_title_error"><li><span class="visually-hidden">Error: </span>'
                      'This field is required.</li></ul>', html)

    def test_radio_select_renders_as_chips_in_fieldset(self):
        form = DemoForm()
        html = self.render_field(form, 'contact_method')
        self.assertIn('<fieldset>', html)
        self.assertIn('<legend class="label">How were you contacted?', html)
        self.assertIn('<div class="choice-chips"><div id="contactMethod">', html)
        self.assertIn('id="contactMethod_0"', html)
        self.assertIn('class="choice-list"', self.render_field(form, 'contact_method', choices='list'))

    def test_checkbox_renders_inline_check(self):
        html = self.render_field(DemoForm(), 'anonymous', help='Your name is hidden.')
        self.assertIn('<label class="check" for="id_anonymous">', html)
        self.assertIn('<p class="help" id="id_anonymous_helptext">Your name is hidden.</p>', html)
        self.assertNotIn('class="req"', html)


@override_settings(STORAGES=PLAIN_STORAGES)
class MainSiteHeaderFooterTests(SimpleTestCase):
    """Every page shows the main Dollar Scholars site's live header and footer."""

    def test_loads_the_main_sites_header_and_footer(self):
        with self.settings(DS_SITE_URL='https://dollarscholars.org'):
            html = render_child()
        self.assertIn('<script src="https://dollarscholars.org/embed/site-header.js" defer></script>', html)
        self.assertIn('<script src="https://dollarscholars.org/embed/site-footer.js" defer></script>', html)
        # This app's own header and footer stay inside, as the fallback.
        header = html[html.index('<ds-site-header>'):html.index('</ds-site-header>')]
        self.assertIn('<header class="site-header">', header)
        footer = html[html.index('<ds-site-footer>'):html.index('</ds-site-footer>')]
        self.assertIn('<footer class="ds-footer">', footer)
        # The dark-mode button moves into the main header's slot for the host's controls.
        self.assertIn("toggle.slot = 'actions'", html)

    def test_empty_ds_site_url_uses_only_this_apps_header_and_footer(self):
        with self.settings(DS_SITE_URL=''):
            html = render_child()
        self.assertNotIn('/embed/site-header.js', html)
        self.assertNotIn('/embed/site-footer.js', html)
        self.assertNotIn("toggle.slot = 'actions'", html)
        self.assertIn('<header class="site-header">', html)
