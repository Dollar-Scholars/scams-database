"""Tests for the scam awareness page (scams/templates/scams/scam_awareness_page.html)
on the Dollar Scholars theme."""
import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve, reverse

# Plain storage so {% static %} works in tests whether or not collectstatic has run
# (the test runner forces DEBUG=False, which makes manifest storages strict).
PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

PAGE_CSS = 'scams/css/pages/awareness.css'
PAGE_JS = 'scams/js/awareness.js'

EXPECTED_RESOURCE_URLS = [
    'https://reportfraud.ftc.gov/',
    'https://www.ic3.gov/',
    'https://www.consumerfinance.gov/',
    'https://www.usa.gov/legal-aid',
]

# (element id, heading text) for every h2 on the page
SECTION_HEADINGS = [
    ('heading-types', 'Common Scams Affecting Immigrants and Families'),
    ('heading-redflags', 'Warning Signs'),
    ('heading-action', 'Clear Steps to Take When Faced with a Scam'),
    ('heading-resources', 'Trusted External Resources'),
]

TOPICS = [
    ('job', 'Fake job &amp; "easy money" offers'),
    ('immigration', 'Scam messages claiming to be from immigration or government agencies'),
    ('tech', 'Calls or texts impersonating banks, utilities, or tech support'),
    ('marketplace', 'Marketplace &amp; payment scams'),
]

CHECKLIST_KEYS = ['urgency', 'payments', 'out-of-nowhere', 'personal-info']


@override_settings(STORAGES=PLAIN_STORAGES)
class ScamAwarenessPageTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = reverse('scam_awareness_page')

    def get_page(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return response, response.content.decode()

    def test_renders_with_base_chrome(self):
        response, html = self.get_page()
        self.assertTemplateUsed(response, 'scams/scam_awareness_page.html')
        self.assertTemplateUsed(response, 'scams/base.html')
        self.assertEqual(html.lower().count('<html'), 1)
        self.assertIn('<title>Stay Informed About Digital Scams | Dollar Scholars</title>', html)
        self.assertIn('<a href="#main-content" class="skip-link">', html)
        self.assertIn('<header class="site-header">', html)
        self.assertIn('<main id="main-content" class="site-main" tabindex="-1">', html)
        self.assertIn('<footer class="ds-footer">', html)
        self.assertIn(f'<link rel="stylesheet" href="{static("scams/css/ds-theme.css")}">', html)
        nav = re.search(r'<nav class="site-nav" aria-label="Main">(.*?)</nav>', html, re.S).group(1)
        self.assertIn(f'<a href="{self.url}" aria-current="page">Scam awareness</a>', nav)

    def test_single_h1_inside_main(self):
        _, html = self.get_page()
        self.assertEqual(len(re.findall(r'<h1[\s>]', html)), 1)
        main = html[html.index('<main id="main-content"'):html.index('</main>')]
        self.assertIn('Stay Informed &amp; Protect Yourself<br>From Future Scams</h1>', main)
        self.assertIn('Read through the topics below to', main)
        # Visitors from the site nav have not just reported anything
        self.assertIn('<p class="eyebrow">Scam awareness</p>', main)
        self.assertNotIn('Thank you for your report', main)

    def test_page_css_and_js_linked_and_exist(self):
        _, html = self.get_page()
        head, body = html.split('</head>', 1)
        self.assertIn(f'<link rel="stylesheet" href="{static(PAGE_CSS)}">', head)
        self.assertIn(f'<script src="{static(PAGE_JS)}" defer></script>', body)
        # page JS comes after the footer, at the end of <body>
        self.assertLess(body.index('</footer>'), body.index(static(PAGE_JS)))
        for asset in (PAGE_CSS, PAGE_JS):
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset), f'{asset} not found by staticfiles finders')

    def test_no_google_fonts_or_inline_styles(self):
        _, html = self.get_page()
        for needle in ('fonts.googleapis.com', 'fonts.gstatic.com', 'Newsreader', 'IBM Plex'):
            with self.subTest(needle=needle):
                self.assertNotIn(needle, html)
        self.assertNotIn('<style', html)
        self.assertNotIn('style="margin: 0;"', html)
        css = Path(finders.find(PAGE_CSS)).read_text(encoding='utf-8')
        self.assertNotIn('@import', css)
        self.assertNotIn('fonts.googleapis.com', css)
        # Dark mode follows the site toggle (html[data-theme]), not the OS media query
        self.assertNotIn('prefers-color-scheme', css)
        self.assertIn('html[data-theme="dark"]', css)

    def test_all_resources_linked(self):
        response, html = self.get_page()
        resources = response.context['resources']
        self.assertEqual([r['url'] for r in resources], EXPECTED_RESOURCE_URLS)
        for resource in resources:
            with self.subTest(resource=resource['name']):
                self.assertIn(
                    f'<a class="resource-card" href="{resource["url"]}" target="_blank" rel="noopener noreferrer">',
                    html)
                self.assertIn(resource['name'], html)
                self.assertIn(resource['description'], html)
        self.assertEqual(html.count('(opens in a new tab)'), len(resources))
        self.assertNotIn('No resources available right now.', html)

    def test_empty_resources_message(self):
        request = RequestFactory().get(self.url)
        request.resolver_match = resolve(self.url)
        html = render_to_string('scams/scam_awareness_page.html', {'resources': []}, request=request)
        self.assertIn('No resources available right now.', html)
        self.assertNotIn('class="resource-card"', html)

    def test_section_headings_and_anchors(self):
        _, html = self.get_page()
        for heading_id, text in SECTION_HEADINGS:
            with self.subTest(heading=heading_id):
                self.assertRegex(html, rf'<h2 class="section-title" id="{heading_id}">{re.escape(text)}</h2>')
                self.assertIn(f'aria-labelledby="{heading_id}"', html)
        self.assertIn('id="contact" aria-labelledby="heading-resources"', html)
        for phrase in ('Tap each example to see what it looks like in real life.',
                       'Check off anything that sounds familiar.',
                       'Use these resources for reporting and support.',
                       'This page is for general awareness only. It is not legal advice.'):
            self.assertIn(phrase, html)

    def test_accordion_hooks_and_topics(self):
        _, html = self.get_page()
        self.assertEqual(html.count('data-accordion-group'), 1)
        self.assertEqual(html.count('data-accordion-item '), len(TOPICS))
        for item_id, title in TOPICS:
            with self.subTest(topic=item_id):
                self.assertIn(f'data-item-id="{item_id}"', html)
                self.assertRegex(
                    html,
                    rf'<button type="button" class="accordion-trigger" data-accordion-trigger aria-expanded="false" '
                    rf'aria-controls="panel-{item_id}" id="trigger-{item_id}">')
                self.assertIn(f'id="panel-{item_id}" role="region" aria-labelledby="trigger-{item_id}"', html)
                self.assertIn(f'<span class="accordion-trigger-text">{title}</span>', html)
        self.assertEqual(html.count('>Reviewed</span>'), len(TOPICS))
        self.assertIn('data-progress-fill', html)
        self.assertIn(f'data-progress-label>0 of {len(TOPICS)} topics reviewed</p>', html)

    def test_warning_checklist_hooks(self):
        _, html = self.get_page()
        for key in CHECKLIST_KEYS:
            with self.subTest(key=key):
                self.assertIn(f'<input type="checkbox" data-checklist-item="{key}">', html)
        self.assertIn('data-reset-checklist>Clear checklist</button>', html)

    def test_steps_and_actions(self):
        _, html = self.get_page()
        for step in ('Stop.', 'Verify independently.', 'Talk to someone you trust.', 'Report it.'):
            self.assertIn(f'<li><strong>{step}</strong>', html)
        main = html[html.index('<main id="main-content"'):html.index('</main>')]
        self.assertRegex(main, rf'<a href="{re.escape(reverse("report_scam"))}" class="btn btn-primary[^"]*">Report a scam</a>')
        self.assertRegex(main, rf'<a href="{re.escape(reverse("dashboard"))}" class="btn btn-secondary[^"]*">View the dashboard</a>')
        self.assertNotIn(reverse('scam_list'), main)
        self.assertNotIn('Back to the Thank You page', main)

    def test_arriving_from_the_thank_you_page(self):
        # thank_you.html links here with ?from=report: thank the reporter, offer the way back
        _, html = self.get_page(**{'from': 'report'})
        main = html[html.index('<main id="main-content"'):html.index('</main>')]
        self.assertIn('<p class="eyebrow">Thank you for your report</p>', main)
        self.assertRegex(main, rf'<a href="{re.escape(reverse("report_scam"))}" class="btn btn-primary[^"]*">Submit Another Report</a>')
        self.assertRegex(main, rf'<a href="{re.escape(reverse("thank_you"))}" class="btn btn-secondary[^"]*">Back to the Thank You page</a>')
        nav = re.search(r'<nav class="site-nav" aria-label="Main">(.*?)</nav>', html, re.S).group(1)
        self.assertIn(f'<a href="{self.url}" aria-current="page">Scam awareness</a>', nav)

    def test_spanish_contact_note(self):
        _, html = self.get_page()
        self.assertIn('lang="es"', html)
        self.assertIn('¿Prefiere esta información en español?', html)
        self.assertIn('<a href="mailto:grezzia@dollarscholars.org">Contáctenos</a>', html)

    def test_page_js_keeps_storage_keys_and_hooks(self):
        js = Path(finders.find(PAGE_JS)).read_text(encoding='utf-8')
        for needle in ("'scamAwarenessProgress_v1'", "'scamAwarenessChecklist_v1'", '.awareness-page',
                       '[data-accordion-item]', '[data-accordion-trigger]', '[data-accordion-panel]',
                       '[data-accordion-group]', '[data-progress-fill]', '[data-progress-label]',
                       '[data-checklist-item]', '[data-reset-checklist]', '.warning-item'):
            with self.subTest(needle=needle):
                self.assertIn(needle, js)
