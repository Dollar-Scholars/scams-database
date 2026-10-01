import unicodedata
from functools import lru_cache

from babel import Locale, UnknownLocaleError
from django import forms
from .models import Scam, COUNTRY_CHOICES, CURRENCY_CHOICES
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import get_language, gettext, gettext_lazy as _
from thefuzz import fuzz
from django.utils import timezone
from datetime import timedelta

SMALL_REPORT_LENGTH = 100


def babel_locale(language_code):
    """The Babel locale for one of our language codes (scams/languages.py), or None.
    zh-hans -> zh_Hans, zh-hant -> zh_Hant, es-mx -> es_MX, the rest as they are."""
    if not language_code:
        return None
    language, _sep, region = language_code.partition('-')
    identifier = language.lower()
    if region:
        identifier += '_' + (region.title() if len(region) == 4 else region.upper())
    try:
        return Locale.parse(identifier)
    except (UnknownLocaleError, ValueError, TypeError):
        return None


def _is_source_language(language_code):
    return not language_code or language_code.split('-')[0] == settings.LANGUAGE_CODE.split('-')[0]


def _sort_key(label):
    """Case- and accent-insensitive sort key, so "Österreich" sorts with the O's."""
    decomposed = unicodedata.normalize('NFKD', str(label))
    return ''.join(c for c in decomposed if not unicodedata.combining(c)).casefold()


@lru_cache(maxsize=None)
def country_choices(language_code):
    """(code, name) for the model's countries, named in the given language (Babel) and
    sorted by that name. English, and any language Babel does not know, keeps the
    model's English names."""
    locale = None if _is_source_language(language_code) else babel_locale(language_code)
    if locale is None:
        return tuple(COUNTRY_CHOICES)
    names = locale.territories
    choices = [(code, names.get(code) or english) for code, english in COUNTRY_CHOICES]
    return tuple(sorted(choices, key=lambda choice: _sort_key(choice[1])))


@lru_cache(maxsize=None)
def currency_names(language_code):
    """{code: name} for the model's currencies in the given language (Babel); {} for
    English and for languages Babel does not know (the model's labels are used)."""
    locale = None if _is_source_language(language_code) else babel_locale(language_code)
    if locale is None:
        return {}
    currencies = locale.currencies
    return {code: currencies[code] for code, _label in CURRENCY_CHOICES if code in currencies}


def currency_choices(language_code):
    """(code, label) for the currency select, e.g. ('USD', 'USD — dólar estadounidense').
    The codes stay the values; "Other" is the model's (translated) label."""
    names = currency_names(language_code)
    choices = []
    for code, label in CURRENCY_CHOICES:
        if code in names:
            params = {'code': code, 'name': names[code]}
            try:
                # Translators: One currency in the currency list, e.g. "USD — US Dollar".
                # %(code)s is the 3-letter currency code, %(name)s the currency's name.
                label = gettext('%(code)s — %(name)s') % params
            except (KeyError, ValueError, TypeError):  # a translation that broke the placeholders
                label = '%(code)s — %(name)s' % params
        choices.append((code, label))
    return choices


class ScamReportForm(forms.ModelForm):
    # Sections of the report page (scams/report_form.html), in page order:
    # (anchor id, title, intro, field names). Every field in Meta.fields must appear once.
    SECTIONS = (
        ('what-happened', _('What happened'), '',
         ('title', 'scam_type', 'date_occurred', 'platform', 'description', 'severity')),
        ('money-lost', _('Money lost'), _('Leave this blank if you did not lose any money.'),
         ('amount_lost', 'currency')),
        ('who-contacted-you', _('Who contacted you'),
         _('Anything you know about the scammer helps others recognise them.'),
         ('contact_method', 'scammer_name', 'scammer_contact')),
        ('about-you', _('About you'), _('Your details are kept private and are never shown on public pages.'),
         ('reporter_name', 'reporter_email', 'reporter_phone', 'country', 'anonymous')),
    )
    # Fields that span both columns of the two-column form grid
    FULL_WIDTH_FIELDS = frozenset({'title', 'platform', 'description', 'severity', 'contact_method', 'anonymous'})
    # Friendlier text for the empty option of optional selects (instead of "---------")
    BLANK_CHOICE_LABELS = {'currency': _('Choose a currency'), 'country': _('Choose a country')}

    class Meta:
        model = Scam
        fields = [
            'title', 'scam_type', 'date_occurred', 'amount_lost',
            'currency', 'platform', 'description', 'severity',
            'scammer_name', 'scammer_contact', 'contact_method',
            'reporter_name', 'reporter_email', 'reporter_phone',
            'country', 'anonymous'
        ]

        widgets = {
            'title': forms.TextInput(attrs={'id': 'id_title', 'placeholder': _('Summarize the scam...')}),
            'scam_type': forms.Select(attrs={'id': 'id_scam_type'}),
            'date_occurred': forms.DateInput(attrs={'type': 'date', 'id': 'id_date_occurred'}),
            'amount_lost': forms.NumberInput(attrs={'id': 'id_amount_lost', 'step': '0.01', 'min': '0',
                                                    'inputmode': 'decimal'}),
            'currency': forms.Select(attrs={'id': 'id_currency'}),
            'platform': forms.TextInput(attrs={'id': 'id_platform'}),
            'description': forms.Textarea(
                attrs={'id': 'id_description', 'rows': 6, 'placeholder': _('Provide as much detail as possible...')}),
            'severity': forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '5', 'id': 'sevRange',
                                                 'oninput': 'updateSeverity(this.value)'}),
            'scammer_name': forms.TextInput(attrs={'id': 'id_scammer_name'}),
            'scammer_contact': forms.TextInput(attrs={'id': 'id_scammer_contact'}),
            'contact_method': forms.RadioSelect(attrs={'id': 'contactMethod'}),
            'reporter_name': forms.TextInput(attrs={'id': 'id_reporter_name', 'autocomplete': 'name'}),
            'reporter_email': forms.EmailInput(attrs={'id': 'id_reporter_email', 'autocomplete': 'email'}),
            'reporter_phone': forms.TextInput(attrs={'id': 'id_reporter_phone', 'autocomplete': 'tel',
                                                     'type': 'tel'}),
            'country': forms.Select(attrs={'id': 'id_country', 'autocomplete': 'country'}),
            'anonymous': forms.CheckboxInput(attrs={'id': 'id_anonymous'}),
        }

        labels = {
            'title': _('Title'),
            'scam_type': _('Type of scam'),
            'date_occurred': _('Date it happened'),
            'platform': _('Platform or website'),
            'description': _('Description'),
            'severity': _('How serious was it?'),
            'amount_lost': _('Amount lost'),
            'currency': _('Currency'),
            'contact_method': _('How did they contact you?'),
            'scammer_name': _('Name they used'),
            'scammer_contact': _('Their phone, email or username'),
            'reporter_name': _('Your name'),
            'reporter_email': _('Your email'),
            'reporter_phone': _('Your phone number'),
            'country': _('Your country'),
            'anonymous': _('Submit anonymously'),
        }

        help_texts = {
            # Translators: The quoted example is a typical report title; translate it too.
            'title': _('A few words that sum it up, for example “Fake parcel delivery text”.'),
            'date_occurred': _('Leave blank if you are not sure.'),
            'platform': _('For example WhatsApp, Facebook Marketplace or a website address.'),
            'description': _('What happened, in order: what they said, what they asked for and what you did. '
                             'At least 20 characters.'),
            'severity': _('1 means little or no harm. 5 means serious harm, such as losing money or personal details.'),
            'amount_lost': _('In the currency you paid in.'),
            'scammer_name': _('Any name, company or username they gave.'),
            'scammer_contact': _('The number, email address, profile or website they used.'),
            'reporter_email': _('Needed so our team can follow up, even if you submit anonymously. '
                                'Never shown publicly.'),
            'anonymous': _('Your name and phone number are not needed. We still need your email so our '
                           'team can follow up, but it is never shown publicly.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Country and currency names in the page's language (Babel). Worked out for each
        # form, not at import, so every request gets its own language.
        language = get_language()
        self.fields['country'].choices = [('', '')] + list(country_choices(language))
        self.fields['currency'].choices = [('', '')] + currency_choices(language)
        for name, text in self.BLANK_CHOICE_LABELS.items():
            field = self.fields[name]
            field.choices = [('', text) if value == '' else (value, label) for value, label in field.choices]
        self._set_aria_attrs()

    def full_clean(self):
        super().full_clean()
        self._set_aria_attrs()

    def _set_aria_attrs(self):
        """Link each control to its help text and errors, which the template renders
        with the ids <auto_id>_helptext and <auto_id>_error."""
        errors = self._errors or {}
        for name, field in self.fields.items():
            auto_id = self[name].auto_id
            attrs = field.widget.attrs
            if not auto_id:
                continue
            described_by = []
            if field.help_text:
                described_by.append(f'{auto_id}_helptext')
            if name in errors:
                described_by.append(f'{auto_id}_error')
                attrs['aria-invalid'] = 'true'
            else:
                attrs.pop('aria-invalid', None)
            if described_by:
                attrs['aria-describedby'] = ' '.join(described_by)
            else:
                attrs.pop('aria-describedby', None)

    def sections(self):
        """The fields grouped into the page's sections (see SECTIONS)."""
        return [
            {'id': key, 'title': title, 'intro': intro, 'fields': [self[name] for name in names]}
            for key, title, intro, names in self.SECTIONS
        ]

    def control_id(self, name):
        """The id of the element to focus for a field (the first radio of a RadioSelect)."""
        bound = self[name]
        widget = bound.field.widget
        control_id = widget.attrs.get('id') or bound.auto_id
        if isinstance(widget, forms.RadioSelect):
            return f'{control_id}_0'
        return control_id

    def error_summary(self):
        """Every error, in page order, for the summary at the top of the page:
        non-field errors first (no link), then one entry per field error."""
        items = [{'label': '', 'message': message, 'anchor': ''} for message in self.non_field_errors()]
        for _, _, _, names in self.SECTIONS:
            for name in names:
                for message in self[name].errors:
                    items.append({'label': self[name].label, 'message': message, 'anchor': self.control_id(name)})
        return items

    def clean_amount_lost(self):
        amount = self.cleaned_data.get('amount_lost')
        if amount is not None and amount < 0:
            raise ValidationError(_("The amount lost cannot be negative."))
        return amount

    def clean_description(self):
        desc = self.cleaned_data.get('description')
        if len(desc) < 20:
            raise ValidationError(_("Please provide a more detailed description (at least 20 characters)."))
        return desc

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount_lost')
        currency = cleaned_data.get('currency')

        if amount and amount > 0 and not currency:
            self.add_error('currency', _("Please select a currency for the reported loss."))

        description = cleaned_data.get('description')
        # No valid description (e.g. too short, so clean_description rejected it):
        # nothing to compare, and an empty one would divide by zero below.
        if not description:
            return cleaned_data

        one_day_ago = timezone.now() - timedelta(days=1)

        recent_scams = Scam.objects.filter(created_at__gte=one_day_ago)

        for scam in recent_scams:
            if not scam.description:
                continue

            description_lengths = [len(description), len(scam.description)]
            smallest_description_length = min(description_lengths)
            largest_description_length = max(description_lengths)
            size_difference = largest_description_length / smallest_description_length

            # If it's much longer then it's not a duplicate
            if size_difference > 4:
                continue

            score = fuzz.token_set_ratio(description, scam.description)

            is_small_report = len(description) < SMALL_REPORT_LENGTH
            if is_small_report:
                threshold = 95
            else:
                threshold = 50

            if score >= threshold:
                self.add_error('description', _("A very similar scam report has already been submitted."))
                break

        return cleaned_data
