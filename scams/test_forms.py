"""Tests for the report form (scams/forms.py) and the report page (scams/report_form.html)."""
import re
from datetime import date, timedelta
from itertools import chain
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ScamReportForm
from .models import Scam

# Plain storage so {% static %} works in tests whether or not collectstatic has run
# (the test runner forces DEBUG=False, which makes manifest storages strict).
PLAIN_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

SHORT_DESCRIPTION_ERROR = "Please provide a more detailed description (at least 20 characters)."
DUPLICATE_ERROR = "A very similar scam report has already been submitted."


def valid_data(**overrides):
    data = {
        'title': 'Fake parcel delivery text',
        'scam_type': 'financial',
        'date_occurred': (date.today() - timedelta(days=3)).isoformat(),
        'amount_lost': '25.00',
        'currency': 'GBP',
        'platform': 'SMS',
        'description': 'A text said my parcel was held and asked me to pay a redelivery fee through a link.',
        'severity': '3',
        'scammer_name': 'Royal Delivery',
        'scammer_contact': '+44 7700 900123',
        'contact_method': 'sms',
        'reporter_name': 'Test User',
        'reporter_email': 'test@example.com',
        'reporter_phone': '555-0199',
        'country': 'GB',
    }
    data.update(overrides)
    return data


class ScamReportFormCleanTests(TestCase):

    def test_short_description_with_recent_report_is_invalid_not_a_crash(self):
        """Regression: clean() divided by zero when the description failed validation
        and a report existed from the last 24 hours."""
        Scam.objects.create(title='Recent', description='Someone called pretending to be my bank.')
        form = ScamReportForm(data=valid_data(description='Too short'))
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['description'], [SHORT_DESCRIPTION_ERROR])

    def test_missing_description_with_recent_report_is_invalid_not_a_crash(self):
        Scam.objects.create(title='Recent', description='Someone called pretending to be my bank.')
        form = ScamReportForm(data=valid_data(description=''))
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)

    def test_recent_report_with_empty_description_is_skipped(self):
        Scam.objects.create(title='Recent, no description', description='')
        form = ScamReportForm(data=valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_still_detected(self):
        description = valid_data()['description']
        Scam.objects.create(title='Recent', description=description)
        form = ScamReportForm(data=valid_data())
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['description'], [DUPLICATE_ERROR])

    def test_currency_required_when_money_lost(self):
        form = ScamReportForm(data=valid_data(currency=''))
        self.assertFalse(form.is_valid())
        self.assertIn('currency', form.errors)


class ScamReportFormPresentationTests(TestCase):

    def test_every_field_is_in_exactly_one_section(self):
        names = list(chain.from_iterable(section[3] for section in ScamReportForm.SECTIONS))
        self.assertEqual(len(names), len(set(names)), 'a field is listed in two sections')
        self.assertEqual(set(names), set(ScamReportForm.Meta.fields))
        self.assertLessEqual(ScamReportForm.FULL_WIDTH_FIELDS, set(names))

    def test_widget_ids_used_by_javascript_are_kept(self):
        html = str(ScamReportForm())
        self.assertIn('id="sevRange"', html)
        self.assertIn('oninput="updateSeverity(this.value)"', html)
        self.assertIn('id="contactMethod"', html)
        self.assertIn('id="contactMethod_0"', html)
        for name in ScamReportForm.Meta.fields:
            if name not in ('severity', 'contact_method'):
                self.assertIn(f'id="id_{name}"', html)

    def test_help_text_and_errors_are_linked_to_the_control(self):
        form = ScamReportForm(data=valid_data(description='Too short', contact_method=''))
        self.assertFalse(form.is_valid())
        attrs = form.fields['description'].widget.attrs
        self.assertEqual(attrs['aria-invalid'], 'true')
        self.assertEqual(attrs['aria-describedby'], 'id_description_helptext id_description_error')
        self.assertEqual(form.fields['contact_method'].widget.attrs['aria-describedby'], 'id_contact_method_error')
        title_attrs = form.fields['title'].widget.attrs
        self.assertNotIn('aria-invalid', title_attrs)
        self.assertEqual(title_attrs['aria-describedby'], 'id_title_helptext')

    def test_aria_attributes_are_per_form_instance(self):
        ScamReportForm(data=valid_data(title='')).is_valid()
        self.assertNotIn('aria-invalid', ScamReportForm().fields['title'].widget.attrs)

    def test_error_summary_in_page_order_with_anchors(self):
        form = ScamReportForm(data=valid_data(title='', description='Too short', contact_method='',
                                              reporter_email='not-an-email'))
        form.is_valid()
        form.add_error(None, 'Something about the whole report.')
        summary = form.error_summary()
        self.assertEqual(summary[0], {'label': '', 'message': 'Something about the whole report.', 'anchor': ''})
        self.assertEqual([item['anchor'] for item in summary[1:]],
                         ['id_title', 'id_description', 'contactMethod_0', 'id_reporter_email'])
        self.assertEqual(summary[2]['message'], SHORT_DESCRIPTION_ERROR)
        self.assertEqual(summary[2]['label'], 'Description')

    def test_error_summary_empty_for_unbound_and_valid_forms(self):
        self.assertEqual(ScamReportForm().error_summary(), [])
        form = ScamReportForm(data=valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.error_summary(), [])


@override_settings(STORAGES=PLAIN_STORAGES)
class ReportPageTests(TestCase):
    url = reverse('report_scam')

    def test_get_renders_with_site_chrome(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'scams/report_form.html')
        self.assertTemplateUsed(response, 'scams/base.html')
        html = response.content.decode()
        self.assertIn('<title>Report a scam | Dollar Scholars</title>', html)
        self.assertIn('<header class="site-header">', html)
        self.assertIn('<footer class="ds-footer">', html)
        self.assertEqual(html.count('<h1'), 1)
        self.assertIn('scams/css/pages/report_form.css', html)
        self.assertIn('scams/js/report_form.js', html)
        self.assertIn('csrfmiddlewaretoken', html)
        self.assertIn('<form method="POST" class="card report-form" novalidate', html)
        for name in ScamReportForm.Meta.fields:
            self.assertIn(f'name="{name}"', html)
        for section_id in ('what-happened', 'money-lost', 'who-contacted-you', 'about-you'):
            self.assertIn(f'id="section-{section_id}"', html)
        self.assertIn('<div class="choice-chips"><div id="contactMethod">', html)
        self.assertIn('id="sevValue"', html)
        self.assertIn(f'href="{reverse("scam_awareness_page")}"', html)
        self.assertNotIn('id="error-summary"', html)
        self.assertNotIn('aria-invalid', html)
        # The star is aria-hidden, so screen readers get the words instead.
        self.assertIn('Fields marked <span class="req" aria-hidden="true">*</span>'
                      '<span class="visually-hidden">with an asterisk</span> are required.', html)

    def test_valid_post_saves_and_redirects_to_thank_you(self):
        response = self.client.post(self.url, valid_data())
        self.assertRedirects(response, reverse('thank_you'), fetch_redirect_response=False)
        scam = Scam.objects.get()
        self.assertEqual(scam.title, 'Fake parcel delivery text')
        self.assertEqual(scam.contact_method, 'sms')
        self.assertEqual(scam.severity, 3)
        self.assertEqual(scam.status, 'pending')

    def test_anonymous_post_with_email_saves_and_redirects(self):
        """Regression: report_form.js switched off (and so never sent) the required email
        when "Submit anonymously" was ticked, so an anonymous report could never be saved."""
        response = self.client.post(self.url, valid_data(anonymous='on', reporter_name='', reporter_phone=''))
        self.assertRedirects(response, reverse('thank_you'), fetch_redirect_response=False)
        scam = Scam.objects.get()
        self.assertTrue(scam.anonymous)
        self.assertEqual(scam.reporter_email, 'test@example.com')

    def test_anonymous_help_says_the_email_is_still_needed(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('<span class="help" id="id_anonymous_helptext">Your name and phone number are not needed. '
                      'We still need your email so our team can follow up, but it is never shown publicly.</span>', html)
        self.assertIn('<p class="help" id="id_reporter_email_helptext">Needed so our team can follow up, '
                      'even if you submit anonymously. Never shown publicly.</p>', html)
        anonymous = re.search(r'<input type="checkbox" name="anonymous"[^>]*>', html).group(0)
        self.assertIn('aria-describedby="id_anonymous_helptext"', anonymous)

    def test_email_error_links_to_an_enabled_control(self):
        response = self.client.post(self.url, valid_data(anonymous='on', reporter_email=''))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Scam.objects.exists())
        html = response.content.decode()
        self.assertIn('href="#id_reporter_email"', html)
        email = re.search(r'<input type="email" name="reporter_email"[^>]*>', html).group(0)
        self.assertIn(' required', email)
        self.assertNotIn('disabled', email)
        # The anonymous toggle greys out the optional name and phone only, never the email.
        js = Path(finders.find('scams/js/report_form.js')).read_text(encoding='utf-8')
        self.assertEqual(re.search(r'var fieldsToGrey = \[(.*?)\];', js).group(1), "'reporter_name', 'reporter_phone'")

    def test_invalid_post_rerenders_with_error_summary(self):
        response = self.client.post(self.url, valid_data(title='', contact_method=''))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Scam.objects.exists())
        html = response.content.decode()
        self.assertIn('<title>Error: Report a scam | Dollar Scholars</title>', html)
        self.assertIn('id="error-summary"', html)
        self.assertIn('There is a problem with your report', html)
        self.assertIn('href="#id_title"', html)
        self.assertIn('href="#contactMethod_0"', html)
        self.assertIn('<ul class="errorlist" id="id_title_error">', html)
        self.assertIn('<ul class="errorlist" id="id_contact_method_error">', html)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_title_helptext id_title_error"', html)
        # Entered values are kept
        self.assertIn('value="Test User"', html)

    def test_short_description_post_with_recent_report_is_not_a_server_error(self):
        """Regression for the HTTP 500 (ZeroDivisionError in ScamReportForm.clean)."""
        Scam.objects.create(title='Recent', description='Someone called pretending to be my bank.')
        response = self.client.post(self.url, valid_data(description='Too short'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="#id_description"')
        self.assertContains(response, SHORT_DESCRIPTION_ERROR)
        self.assertEqual(Scam.objects.count(), 1)

    def test_reporter_details_not_echoed_outside_their_inputs(self):
        """The page only shows reporter details inside the form's own inputs."""
        response = self.client.post(self.url, valid_data(title=''))
        html = response.content.decode()
        self.assertEqual(html.count('test@example.com'), 1)
        self.assertIn('value="test@example.com"', html)


class ReportPageWordingTests(TestCase):
    def test_what_happens_next_says_scamdb_generates_reports(self):
        response = self.client.get(reverse('report_scam'))
        self.assertContains(
            response, 'ScamDB generates reports on the latest scams to help other individuals and organizations.')
