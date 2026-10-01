"""Tests for the "All reports" list page (scam_list) and the thank-you page (thank_you)."""
import re
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.db import connection
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Scam
from .views import REPORTS_PER_PAGE

# Plain storage so {% static %} works in tests whether or not collectstatic has run
# (the test runner forces DEBUG=False, which makes manifest storages strict).
PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

PII = {
    'reporter_name': 'Rita Reporter',
    'reporter_email': 'rita.reporter@example.com',
    'reporter_phone': '+1 555 0199 777',
}


def make_scam(title='Fake parcel fee', **fields):
    values = {
        'title': title,
        'description': 'A text said a parcel was held until a fee was paid.',
        'scam_type': 'identity',
        'contact_method': 'sms',
        'date_occurred': date(2026, 5, 20),
        'country': 'GB',
        **PII,
    }
    values.update(fields)
    return Scam.objects.create(**values)


def main_html(response):
    """Only the page's own content (<main>), not the shared header/footer links."""
    html = response.content.decode()
    match = re.search(r'<main id="main-content"[^>]*>(.*?)</main>', html, re.S)
    assert match, '<main> not found'
    return match.group(1)


def row_titles(response):
    return re.findall(r'<th scope="row" class="report-title">(.*?)</th>', main_html(response), re.S)


@override_settings(STORAGES=PLAIN_STORAGES)
class ScamListAccessTests(TestCase):
    url = reverse('scam_list')

    def test_anonymous_visitors_are_sent_to_the_admin_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("admin:login")}?next={self.url}')

    def test_logged_in_non_staff_users_are_refused(self):
        user = get_user_model().objects.create_user('visitor', password='x')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('admin:login')))

    def test_staff_can_see_it(self):
        self.client.force_login(get_user_model().objects.create_user('staff', password='x', is_staff=True))
        self.assertEqual(self.client.get(self.url).status_code, 200)


class ScamListPageTests(TestCase):
    url = reverse('scam_list')

    def setUp(self):
        # The page is staff only for now
        self.client.force_login(get_user_model().objects.create_user('staff', password='x', is_staff=True))

    def make_many(self, count):
        """`count` reports; "Report 1" is the oldest, "Report <count>" the newest."""
        start = timezone.now() - timedelta(days=count)
        for i in range(1, count + 1):
            scam = make_scam(title=f'Report {i}')
            Scam.objects.filter(pk=scam.pk).update(created_at=start + timedelta(days=i))

    def test_uses_theme_and_one_h1(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'scams/base.html')
        html = response.content.decode()
        self.assertIn('<title>All reports | Dollar Scholars</title>', html)
        self.assertEqual(html.count('<h1'), 1)
        self.assertIn('<p class="eyebrow">Scam Reports</p>', html)
        self.assertIn('scams/css/pages/scam_list.css', html)
        self.assertIsNotNone(finders.find('scams/css/pages/scam_list.css'))

    def test_empty_state_with_report_cta(self):
        response = self.client.get(self.url)
        main = main_html(response)
        self.assertIn('class="empty-state"', main)
        self.assertIn('No reports yet', main)
        self.assertIn(f'<a class="btn btn-primary" href="{reverse("report_scam")}">Report a scam</a>', main)
        self.assertNotIn('<table', main)
        self.assertNotIn('class="pagination"', main)

    def test_rows_show_display_values(self):
        make_scam(title='Crypto group promising 30% a week', scam_type='investment',
                  contact_method='messaging', date_occurred=date(2026, 3, 4), country='US')
        response = self.client.get(self.url)
        main = main_html(response)
        self.assertIn('<table class="table table-stack reports-table">', main)
        self.assertIn('Crypto group promising 30% a week', main)
        self.assertIn('Investment and wealth scams', main)
        self.assertIn('Messaging app', main)
        self.assertIn('United States', main)
        self.assertIn('<span class="badge badge-dot badge-pending">Pending</span>', main)
        for header in ('Title', 'Type', 'Contact method', 'Date occurred', 'Country', 'Status'):
            self.assertIn(f'<th scope="col">{header}</th>', main)
        self.assertIn('1 report</strong>', main)

    def test_shows_date_occurred_not_removed_date_seen(self):
        make_scam(date_occurred=date(2026, 5, 20))
        main = main_html(self.client.get(self.url))
        self.assertIn('<time datetime="2026-05-20">May 20, 2026</time>', main)
        self.assertNotIn('Date Seen', main)
        # date_seen was dropped in migration 0006; the template must not reference it.
        self.assertNotIn('date_seen', get_template('scams/scam_list.html').template.source)

    def test_every_data_cell_is_labelled_for_mobile(self):
        make_scam()
        make_scam(title='Second')
        main = main_html(self.client.get(self.url))
        cells = re.findall(r'<td\b[^>]*>', main)
        self.assertEqual(len(cells), 2 * 5)
        for cell in cells:
            self.assertIn('data-label="', cell)

    def test_missing_values_show_not_given(self):
        make_scam(title='Bare report', date_occurred=None, country='', contact_method='undefined',
                  scam_type='undefined')
        main = main_html(self.client.get(self.url))
        self.assertEqual(main.count('<span class="text-muted">Not given</span>'), 4)
        self.assertNotIn('None', main)
        self.assertNotIn('undefined', main)

    def test_never_shows_reporter_pii(self):
        make_scam()
        make_scam(title='Another', anonymous=True)
        response = self.client.get(self.url)
        html = response.content.decode()
        for value in PII.values():
            self.assertNotIn(value, html)
        self.assertNotIn('rita.reporter', html)
        self.assertNotIn('555 0199', html)

    def test_reporter_columns_are_not_even_queried(self):
        make_scam()
        with CaptureQueriesContext(connection) as queries:
            self.client.get(self.url)
        sql = ' '.join(q['sql'] for q in queries.captured_queries if 'scams_scam' in q['sql'])
        self.assertIn('"title"', sql)
        for column in ('reporter_name', 'reporter_email', 'reporter_phone', 'description'):
            self.assertNotIn(column, sql)

    def test_titles_are_escaped(self):
        make_scam(title='<script>alert(1)</script>')
        html = self.client.get(self.url).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_no_pager_for_a_single_page(self):
        self.make_many(REPORTS_PER_PAGE)
        response = self.client.get(self.url)
        self.assertEqual(len(row_titles(response)), REPORTS_PER_PAGE)
        self.assertNotIn('class="pagination"', main_html(response))
        self.assertIn(f'Showing 1&ndash;{REPORTS_PER_PAGE} of {REPORTS_PER_PAGE}', main_html(response))

    def test_paginates_newest_first(self):
        self.assertEqual(REPORTS_PER_PAGE, 25)
        self.make_many(30)

        first = self.client.get(self.url)
        titles = row_titles(first)
        self.assertEqual(len(titles), 25)
        self.assertEqual(titles[0], 'Report 30')
        self.assertEqual(titles[-1], 'Report 6')
        main = main_html(first)
        self.assertIn('30 reports</strong>', main)
        self.assertIn('Showing 1&ndash;25 of 30', main)
        self.assertIn('<nav class="pager" aria-label="Pagination">', main)
        self.assertIn('<a href="?page=1" aria-current="page" aria-label="Page 1">1</a>', main)
        self.assertIn('<a href="?page=2" aria-label="Page 2">2</a>', main)
        self.assertIn('<a class="pager-next" href="?page=2" rel="next" aria-label="Next page">Next</a>', main)
        self.assertIn('<span class="pager-prev is-disabled">Previous</span>', main)
        self.assertIn('Page 1 of 2', main)

        second = self.client.get(self.url, {'page': 2})
        self.assertEqual(row_titles(second), [f'Report {i}' for i in range(5, 0, -1)])
        main = main_html(second)
        self.assertIn('Showing 26&ndash;30 of 30', main)
        self.assertIn('<a href="?page=2" aria-current="page" aria-label="Page 2">2</a>', main)
        self.assertIn('<a class="pager-prev" href="?page=1" rel="prev" aria-label="Previous page">Previous</a>', main)
        self.assertIn('<span class="pager-next is-disabled">Next</span>', main)

    def test_long_page_ranges_are_elided(self):
        self.make_many(REPORTS_PER_PAGE * 9)
        main = main_html(self.client.get(self.url, {'page': 5}))
        self.assertIn('aria-current="page" aria-label="Page 5"', main)
        self.assertEqual(main.count('<span class="pagination-ellipsis">&hellip;</span>'), 2)
        for shown in (1, 4, 5, 6, 9):
            self.assertIn(f'aria-label="Page {shown}"', main)
        for hidden in (2, 3, 7, 8):
            self.assertNotIn(f'aria-label="Page {hidden}"', main)

    def test_bad_page_values_never_error(self):
        self.make_many(30)
        cases = {
            'abc': 1, '': 1, '1.5': 1, '2.0': 1, ' ': 1,
            '0': 2, '-1': 2, '3': 2, '999': 2, '99999999999999999999999': 2,
        }
        for value, expected_page in cases.items():
            with self.subTest(page=value):
                response = self.client.get(self.url, {'page': value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['page_obj'].number, expected_page)
                expected_rows = 25 if expected_page == 1 else 5
                self.assertEqual(len(row_titles(response)), expected_rows)

    def test_bad_page_value_on_empty_list(self):
        for value in ('abc', '0', '5'):
            with self.subTest(page=value):
                response = self.client.get(self.url, {'page': value})
                self.assertEqual(response.status_code, 200)
                self.assertIn('No reports yet', main_html(response))


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
        self.assertNotIn(f'href="{reverse("scam_list")}"', main)

    def test_report_nav_item_marked_as_current_section(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn(f'<a href="{reverse("report_scam")}" aria-current="true">Report a scam</a>', html)
