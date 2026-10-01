"""Tests for the dashboard page: scams.views.dashboard and scams/templates/scams/dashboard.html."""
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal

from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Scam

# Plain storage so {% static %} works in tests whether or not collectstatic has run
# (the test runner forces DEBUG=False, which makes manifest storages strict).
PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

REPORTER_PII = {
    'reporter_name': 'Priscilla Reporterson',
    'reporter_email': 'priscilla.private@example.com',
    'reporter_phone': '+1 555 0142 777',
}

LEGACY_CONTEXT_KEYS = [
    'scams', 'years', 'months', 'selected_year', 'selected_month',
    'scams_o', 'years_o', 'months_o', 'selected_year_o', 'selected_month_o',
    'chart_labels', 'chart_data', 'chart_labels_o', 'chart_data_o',
    'total_loss', 'total_loss_o', 'total_scams_o',
]


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def make_scam(title='A scam', created=None, occurred=None, amount=None, currency='', **extra):
    fields = {
        'title': title,
        'description': 'Someone asked me for money.',
        'date_occurred': occurred,
        'amount_lost': amount,
        'currency': currency,
        **REPORTER_PII,
    }
    fields.update(extra)
    scam = Scam.objects.create(**fields)
    if created is not None:
        # created_at is auto_now_add, so it can only be changed after the insert.
        Scam.objects.filter(pk=scam.pk).update(created_at=created)
        scam.refresh_from_db()
    return scam


def chart_payload(response):
    """The JSON the template hands to dashboard.js via json_script."""
    match = re.search(
        r'<script id="dashboard-chart-data" type="application/json">(.*?)</script>',
        response.content.decode(), re.S,
    )
    assert match, 'chart data <script> not found'
    return json.loads(match.group(1))


@override_settings(STORAGES=PLAIN_STORAGES)
class DashboardViewTests(TestCase):

    def get(self, **params):
        response = self.client.get(reverse('dashboard'), params)
        self.assertEqual(response.status_code, 200)
        return response

    # --- robustness ----------------------------------------------------------------

    def test_empty_database_renders_empty_states(self):
        response = self.get()
        self.assertTemplateUsed(response, 'scams/dashboard.html')
        self.assertTemplateUsed(response, 'scams/base.html')
        self.assertContains(response, 'No reports yet')
        self.assertEqual(response.context['total_scams'], 0)
        self.assertEqual(response.context['loss_by_currency'], [])
        # No canvas without data, so dashboard.js has nothing to draw.
        self.assertNotContains(response, '<canvas')

    def test_rows_without_date_occurred_render(self):
        make_scam('Undated', created=utc(2026, 3, 5, 12), occurred=None, amount=Decimal('10'), currency='USD')
        make_scam('Dated', created=utc(2026, 3, 6, 12), occurred=date(2026, 2, 14))

        response = self.get()
        self.assertNotIn(None, list(response.context['years_o']))
        self.assertNotIn(None, [num for num, _ in response.context['months_o']])
        self.assertEqual(json.loads(response.context['chart_labels_o']), ['Feb 2026'])
        self.assertEqual(response.context['total_scams_o'], 2)
        self.assertEqual(response.context['undated_count_o'], 1)
        self.assertContains(response, '1 with no date given')

        # Filtering by the occurred date leaves the undated row out.
        response = self.get(year_o='2026')
        self.assertEqual(response.context['total_scams_o'], 1)
        self.assertEqual(response.context['undated_count_o'], 0)

    def test_only_undated_rows_render(self):
        make_scam('Undated', occurred=None)
        response = self.get()
        self.assertEqual(list(response.context['years_o']), [])
        self.assertEqual(response.context['months_o'], [])
        self.assertEqual(json.loads(response.context['chart_data_o']), [])
        self.assertContains(response, 'No dates to chart')

    def test_invalid_params_are_ignored(self):
        make_scam('One', created=utc(2026, 3, 5, 12), occurred=date(2026, 3, 1))
        make_scam('Two', created=utc(2025, 7, 5, 12), occurred=date(2025, 6, 1))
        bad_values = [
            {'year': 'abc'}, {'year': '0'}, {'year': '99999'}, {'year': '-2026'}, {'year': '2026.5'},
            {'month': '13'}, {'month': '0'}, {'month': 'March'},
            {'year_o': 'x'}, {'year_o': '10000'}, {'month_o': '-1'}, {'month_o': '1e1'},
            {'year': '', 'month': '', 'year_o': '', 'month_o': ''},
        ]
        for params in bad_values:
            with self.subTest(params=params):
                response = self.get(**params)
                ctx = response.context
                self.assertEqual(ctx['total_scams'], 2)
                self.assertEqual(ctx['total_scams_o'], 2)
                for key in ('selected_year', 'selected_month', 'selected_year_o', 'selected_month_o'):
                    self.assertIsNone(ctx[key])

    def test_valid_filter_without_data_is_still_shown_as_selected(self):
        make_scam('One', created=utc(2026, 3, 5, 12))
        response = self.get(year='2019')
        self.assertIn(2019, response.context['years'])
        self.assertContains(response, '<option value="2019" selected>')
        self.assertContains(response, 'No reports match these filters')
        self.assertEqual(response.context['total_scams'], 0)

    # --- filters ---------------------------------------------------------------------

    def test_submitted_filters_narrow_results(self):
        make_scam('Old', created=utc(2025, 3, 10, 12))
        make_scam('March', created=utc(2026, 3, 5, 12))
        make_scam('July', created=utc(2026, 7, 1, 12))

        self.assertEqual(self.get().context['total_scams'], 3)

        response = self.get(year='2026')
        self.assertEqual(response.context['total_scams'], 2)
        self.assertEqual(response.context['selected_year'], '2026')
        self.assertEqual(response.context['months'], [(3, 'Mar'), (7, 'Jul')])
        self.assertEqual(response.context['years'], [2026, 2025])

        response = self.get(year='2026', month='3')
        self.assertEqual(response.context['total_scams'], 1)
        self.assertEqual([s.title for s in response.context['recent_scams']], ['March'])
        self.assertContains(response, '<option value="3" selected>')

        # Month on its own spans every year.
        self.assertEqual(self.get(month='3').context['total_scams'], 2)

    def test_occurred_filters_narrow_results(self):
        make_scam('A', occurred=date(2024, 12, 24))
        make_scam('B', occurred=date(2025, 12, 1))
        make_scam('C', occurred=date(2025, 5, 1))
        make_scam('Undated', occurred=None)

        self.assertEqual(self.get(year_o='2025').context['total_scams_o'], 2)
        self.assertEqual(self.get(year_o='2025', month_o='12').context['total_scams_o'], 1)
        self.assertEqual(self.get(month_o='12').context['total_scams_o'], 2)
        self.assertEqual(self.get(year_o='2025').context['months_o'], [(5, 'May'), (12, 'Dec')])

    def test_each_filter_form_keeps_the_other_cards_filter(self):
        make_scam('A', created=utc(2026, 3, 5, 12), occurred=date(2025, 5, 1))
        response = self.get(year='2026', month='3', year_o='2025', month_o='5')
        html = response.content.decode()
        self.assertIn('<input type="hidden" name="year_o" value="2025">', html)
        self.assertIn('<input type="hidden" name="month_o" value="5">', html)
        self.assertIn('<input type="hidden" name="year" value="2026">', html)
        self.assertIn('<input type="hidden" name="month" value="3">', html)
        # Each reset link clears only its own card's filter.
        self.assertEqual(response.context['reset_query'], 'year_o=2025&month_o=5')
        self.assertEqual(response.context['reset_query_o'], 'year=2026&month=3')

    def test_date_occurred_ordering_puts_nulls_last(self):
        make_scam('Undated', occurred=None)
        make_scam('Older', occurred=date(2024, 1, 1))
        make_scam('Newer', occurred=date(2025, 1, 1))
        titles = [s.title for s in self.get().context['scams_o']]
        self.assertEqual(titles, ['Newer', 'Older', 'Undated'])

    def test_recent_reports_are_newest_first_and_capped(self):
        for day in range(1, 13):
            make_scam(f'Day {day}', created=utc(2026, 3, day, 12))
        recent = list(self.get().context['recent_scams'])
        self.assertEqual(len(recent), 10)
        self.assertEqual(recent[0].title, 'Day 12')
        self.assertContains(self.get(), 'Showing the 10 most recent of 12')

    # --- money -----------------------------------------------------------------------

    def test_losses_are_totalled_per_currency(self):
        make_scam('US 1', created=utc(2026, 3, 5, 12), occurred=date(2026, 3, 1), amount=Decimal('100.00'), currency='USD')
        make_scam('US 2', created=utc(2026, 3, 6, 12), occurred=date(2026, 3, 2), amount=Decimal('50.50'), currency='USD')
        make_scam('Euro', created=utc(2026, 3, 7, 12), occurred=date(2026, 3, 3), amount=Decimal('20.00'), currency='EUR')
        make_scam('Big', created=utc(2026, 3, 8, 12), occurred=date(2026, 3, 4), amount=Decimal('1234567.00'), currency='NGN')
        make_scam('No amount', created=utc(2026, 3, 8, 12), amount=None, currency='GBP')
        make_scam('No currency', created=utc(2026, 3, 9, 12), amount=Decimal('5.00'), currency='')

        response = self.get()
        rows = response.context['loss_by_currency']
        self.assertEqual(
            [(r['code'], r['total'], r['count']) for r in rows],
            [('USD', Decimal('150.50'), 2), ('EUR', Decimal('20.00'), 1),
             ('NGN', Decimal('1234567.00'), 1), ('', Decimal('5.00'), 1)],
        )
        self.assertEqual(rows[-1]['label'], 'Currency not given')
        self.assertEqual(rows[0]['label'], 'US Dollar')
        self.assertEqual(response.context['loss_by_currency_o'][0]['code'], 'USD')
        # GBP has no amount, so it is not listed.
        self.assertNotIn('GBP', [r['code'] for r in rows])

        # Legacy mixed-currency totals stay in the context but are not displayed.
        self.assertEqual(response.context['total_loss'], Decimal('1234742.50'))
        html = response.content.decode()
        self.assertIn('150.50', html)
        self.assertIn('20.00', html)
        self.assertIn('1,234,567.00', html)
        self.assertNotIn('1234742.50', html)
        self.assertNotIn('1,234,742.50', html)
        # The two loss tiles say which date each one follows.
        self.assertIn('id="loss-heading">Money lost &middot; by date submitted</p>', html)
        self.assertIn('id="loss-heading-o">Money lost &middot; by date occurred</p>', html)

    def test_currency_not_given_is_last_and_zero_amounts_are_not_counted(self):
        for day in (1, 2, 3):
            make_scam(f'No currency {day}', created=utc(2026, 3, day, 12), amount=Decimal('5.00'), currency='')
        make_scam('Euro', created=utc(2026, 3, 4, 12), amount=Decimal('20.00'), currency='EUR')
        make_scam('Zero euro', created=utc(2026, 3, 5, 12), amount=Decimal('0'), currency='EUR')
        make_scam('Zero pound', created=utc(2026, 3, 6, 12), amount=Decimal('0.00'), currency='GBP')
        make_scam('Zero, no currency', created=utc(2026, 3, 7, 12), amount=Decimal('0'), currency='')

        rows = self.get().context['loss_by_currency']
        # "Currency not given" has the most reports but still comes after every real currency.
        self.assertEqual(
            [(r['code'], r['total'], r['count']) for r in rows],
            [('EUR', Decimal('20.00'), 1), ('', Decimal('15.00'), 3)],
        )

    def test_losses_follow_each_cards_filter(self):
        make_scam('A', created=utc(2026, 3, 5, 12), occurred=date(2024, 1, 1), amount=Decimal('10'), currency='USD')
        make_scam('B', created=utc(2025, 3, 5, 12), occurred=date(2025, 1, 1), amount=Decimal('7'), currency='EUR')
        response = self.get(year='2026', year_o='2025')
        self.assertEqual([r['code'] for r in response.context['loss_by_currency']], ['USD'])
        self.assertEqual([r['code'] for r in response.context['loss_by_currency_o']], ['EUR'])

    # --- charts ----------------------------------------------------------------------

    def test_chart_data_is_passed_safely_and_fills_empty_months(self):
        make_scam('Jan', created=utc(2026, 1, 15, 12), occurred=date(2025, 11, 2))
        make_scam('Mar', created=utc(2026, 3, 15, 12), occurred=date(2026, 1, 20))
        make_scam('Mar 2', created=utc(2026, 3, 16, 12), occurred=date(2026, 1, 21))

        response = self.get()
        payload = chart_payload(response)
        self.assertEqual(payload['submitted']['labels'], ['Jan 2026', 'Feb 2026', 'Mar 2026'])
        self.assertEqual(payload['submitted']['data'], [1, 0, 2])
        self.assertEqual(payload['occurred']['labels'], ['Nov 2025', 'Dec 2025', 'Jan 2026'])
        self.assertEqual(payload['occurred']['data'], [1, 0, 2])

        # Legacy JSON-string keys carry the same series.
        self.assertEqual(json.loads(response.context['chart_labels']), payload['submitted']['labels'])
        self.assertEqual(json.loads(response.context['chart_data']), payload['submitted']['data'])
        self.assertEqual(json.loads(response.context['chart_labels_o']), payload['occurred']['labels'])
        self.assertEqual(json.loads(response.context['chart_data_o']), payload['occurred']['data'])

        html = response.content.decode()
        self.assertIn('https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js', html)
        self.assertRegex(html, r'<canvas id="scamChart" role="img" aria-label="[^"]+Jan 2026 to Mar 2026')
        self.assertRegex(html, r'<canvas id="scamChart_o" role="img" aria-label="[^"]+Nov 2025 to Jan 2026')
        # Data table fallback for each chart.
        self.assertEqual(html.count('<details class="chart-data"'), 2)
        self.assertIn('<td data-label="Reports" class="num">2</td>', html)

    def test_single_month_shows_a_figure_not_a_chart(self):
        make_scam('A', created=utc(2026, 3, 5, 12), occurred=date(2025, 3, 1))
        make_scam('B', created=utc(2026, 3, 6, 12), occurred=date(2025, 3, 2))
        make_scam('Undated', created=utc(2026, 3, 7, 12), occurred=None)
        response = self.get()
        self.assertNotContains(response, '<canvas')
        self.assertContains(response, 'reports submitted in Mar 2026')
        self.assertContains(response, 'scams reported as happening in Mar 2025')
        self.assertContains(response, '1 report with no date given is not in this chart.')

    def test_month_filter_does_not_chart_other_months(self):
        make_scam('March', created=utc(2026, 3, 5, 12), occurred=date(2026, 3, 1))
        make_scam('April', created=utc(2026, 4, 5, 12), occurred=date(2026, 4, 1))

        response = self.get(month='3', month_o='3')
        self.assertEqual(response.context['chart_rows'], [('Mar 2026', 1)])
        self.assertEqual(response.context['chart_rows_o'], [('Mar 2026', 1)])
        payload = chart_payload(response)
        self.assertEqual(payload['submitted']['labels'], ['Mar 2026'])
        self.assertEqual(payload['occurred']['labels'], ['Mar 2026'])
        self.assertNotContains(response, 'Apr 2026')

    def test_month_filter_without_year_fills_that_month_of_each_year(self):
        make_scam('Mar 2024', created=utc(2024, 3, 5, 12), occurred=date(2024, 3, 1))
        make_scam('Mar 2026', created=utc(2026, 3, 5, 12), occurred=date(2026, 3, 1))
        make_scam('Apr 2026', created=utc(2026, 4, 5, 12), occurred=date(2026, 4, 1))

        payload = chart_payload(self.get(month='3', month_o='3'))
        for key in ('submitted', 'occurred'):
            with self.subTest(chart=key):
                self.assertEqual(payload[key]['labels'], ['Mar 2024', 'Mar 2025', 'Mar 2026'])
                self.assertEqual(payload[key]['data'], [1, 0, 1])

    def test_very_long_date_ranges_are_not_padded(self):
        make_scam('Ancient', occurred=date(1901, 1, 1))
        make_scam('Recent', occurred=date(2026, 1, 1))
        payload = chart_payload(self.get())
        self.assertEqual(payload['occurred']['labels'], ['Jan 1901', 'Jan 2026'])
        # Also with a month filter: not 126 bars of mostly zeros.
        payload = chart_payload(self.get(month_o='1'))
        self.assertEqual(payload['occurred']['labels'], ['Jan 1901', 'Jan 2026'])

    def test_user_text_is_escaped(self):
        make_scam('</script><script>alert("x")</script>', created=utc(2026, 3, 5, 12))
        html = self.get().content.decode()
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertIn('&lt;/script&gt;&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;', html)

    # --- privacy and contract ------------------------------------------------------

    def test_no_reporter_pii_in_html(self):
        make_scam('Visible title', created=utc(2026, 3, 5, 12), occurred=date(2026, 3, 1),
                  amount=Decimal('9.99'), currency='GBP')
        for params in ({}, {'year': '2026'}, {'year_o': '2026', 'month_o': '3'}):
            with self.subTest(params=params):
                response = self.get(**params)
                self.assertContains(response, 'Visible title')
                for value in REPORTER_PII.values():
                    self.assertNotContains(response, value)

    def test_legacy_context_keys_are_kept(self):
        make_scam('A', created=utc(2026, 3, 5, 12), occurred=date(2026, 3, 1))
        response = self.get(year='2026', month='3', year_o='2026', month_o='3')
        for key in LEGACY_CONTEXT_KEYS:
            self.assertIn(key, response.context, key)
        self.assertEqual(response.context['selected_month_o'], '3')
        self.assertEqual(response.context['total_scams_o'], 1)

    def test_page_uses_theme_and_own_static_files(self):
        make_scam('A', created=utc(2026, 3, 5, 12))
        response = self.get()
        self.assertContains(response, '<title>Scam dashboard | Dollar Scholars</title>', html=False)
        self.assertEqual(response.content.decode().count('<h1'), 1)
        self.assertContains(response, 'scams/css/pages/dashboard.css')
        self.assertContains(response, 'scams/js/dashboard.js')
        self.assertContains(response, 'aria-current="page"')
        for path in ('scams/css/pages/dashboard.css', 'scams/js/dashboard.js'):
            self.assertIsNotNone(finders.find(path), path)
