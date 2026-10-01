"""Tests for the thank-you page, and that the removed All reports page is gone."""
import re

from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse

# Plain storage so {% static %} works in tests whether or not collectstatic has run
# (the test runner forces DEBUG=False, which makes manifest storages strict).
PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


def main_html(response):
    """Only the page's own content (<main>), not the shared header/footer links."""
    html = response.content.decode()
    match = re.search(r'<main id="main-content"[^>]*>(.*?)</main>', html, re.S)
    assert match, '<main> not found'
    return match.group(1)


class RemovedAllReportsPageTests(TestCase):
    def test_old_address_is_gone(self):
        self.assertEqual(self.client.get('/all-scams/').status_code, 404)

    def test_no_page_links_to_it(self):
        for name in ('report_scam', 'dashboard', 'thank_you', 'scam_awareness_page', 'contributors'):
            self.assertNotContains(self.client.get(reverse(name)), 'href="/all-scams/"', msg_prefix=name)


@override_settings(STORAGES=PLAIN_STORAGES)
class ThankYouPageTests(TestCase):
    url = reverse('thank_you')

    def test_renders_in_theme(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'scams/base.html')
        html = response.content.decode()
        self.assertIn('<title>Thank you | Dollar Scholars</title>', html)
        self.assertEqual(html.count('<h1'), 1)
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertIn('scams/css/pages/thank_you.css', html)
        self.assertIsNotNone(finders.find('scams/css/pages/thank_you.css'))

    def test_keeps_confirmation_and_spanish_copy(self):
        main = main_html(self.client.get(self.url))
        self.assertIn('class="thanks-icon"', main)
        self.assertIn('Your report has been submitted successfully and is currently pending review.', main)
        self.assertIn('Su informe ha sido enviado y actualmente está en espera de revisión.', main)
        self.assertIn('What happens next', main)

    def test_call_to_action_links(self):
        main = main_html(self.client.get(self.url))
        self.assertIn(f'<a class="btn btn-primary" href="{reverse("report_scam")}">Submit another report</a>', main)
        self.assertIn(f'<a class="btn btn-secondary" href="{reverse("dashboard")}">View the dashboard</a>', main)
        self.assertIn(
            f'<a class="btn btn-secondary" href="{reverse("scam_awareness_page")}?from=report">'
            'Learn how to protect yourself from future scams</a>', main)
        self.assertIn(f'href="{reverse("dashboard")}">dashboard</a>', main)
        self.assertNotIn('href="/all-scams/"', main)

    def test_report_nav_item_marked_as_current_section(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn(f'<a href="{reverse("report_scam")}" aria-current="true">Report a scam</a>', html)
