from django import forms
from .models import Scam
from django.core.exceptions import ValidationError
from thefuzz import fuzz
from django.utils import timezone
from datetime import timedelta

SMALL_REPORT_LENGTH = 100

class ScamReportForm(forms.ModelForm):
    # Sections of the report page (scams/report_form.html), in page order:
    # (anchor id, title, intro, field names). Every field in Meta.fields must appear once.
    SECTIONS = (
        ('what-happened', 'What happened', '',
         ('title', 'scam_type', 'date_occurred', 'platform', 'description', 'severity')),
        ('money-lost', 'Money lost', 'Leave this blank if you did not lose any money.',
         ('amount_lost', 'currency')),
        ('who-contacted-you', 'Who contacted you', 'Anything you know about the scammer helps others recognise them.',
         ('contact_method', 'scammer_name', 'scammer_contact')),
        ('about-you', 'About you', 'Your details are kept private and are never shown on public pages.',
         ('reporter_name', 'reporter_email', 'reporter_phone', 'country', 'anonymous')),
    )
    # Fields that span both columns of the two-column form grid
    FULL_WIDTH_FIELDS = frozenset({'title', 'platform', 'description', 'severity', 'contact_method', 'anonymous'})
    # Friendlier text for the empty option of optional selects (instead of "---------")
    BLANK_CHOICE_LABELS = {'currency': 'Choose a currency', 'country': 'Choose a country'}

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
            'title': forms.TextInput(attrs={'id': 'id_title', 'placeholder': 'Summarize the scam...'}),
            'scam_type': forms.Select(attrs={'id': 'id_scam_type'}),
            'date_occurred': forms.DateInput(attrs={'type': 'date', 'id': 'id_date_occurred'}),
            'amount_lost': forms.NumberInput(attrs={'id': 'id_amount_lost', 'step': '0.01', 'min': '0',
                                                    'inputmode': 'decimal'}),
            'currency': forms.Select(attrs={'id': 'id_currency'}),
            'platform': forms.TextInput(attrs={'id': 'id_platform'}),
            'description': forms.Textarea(
                attrs={'id': 'id_description', 'rows': 6, 'placeholder': 'Provide as much detail as possible...'}),
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
            'title': 'Title',
            'scam_type': 'Type of scam',
            'date_occurred': 'Date it happened',
            'platform': 'Platform or website',
            'description': 'Description',
            'severity': 'How serious was it?',
            'amount_lost': 'Amount lost',
            'currency': 'Currency',
            'contact_method': 'How did they contact you?',
            'scammer_name': 'Name they used',
            'scammer_contact': 'Their phone, email or username',
            'reporter_name': 'Your name',
            'reporter_email': 'Your email',
            'reporter_phone': 'Your phone number',
            'country': 'Your country',
            'anonymous': 'Submit anonymously',
        }

        help_texts = {
            'title': 'A few words that sum it up, for example “Fake parcel delivery text”.',
            'date_occurred': 'Leave blank if you are not sure.',
            'platform': 'For example WhatsApp, Facebook Marketplace or a website address.',
            'description': 'What happened, in order: what they said, what they asked for and what you did. '
                           'At least 20 characters.',
            'severity': '1 means little or no harm. 5 means serious harm, such as losing money or personal details.',
            'amount_lost': 'In the currency you paid in.',
            'scammer_name': 'Any name, company or username they gave.',
            'scammer_contact': 'The number, email address, profile or website they used.',
            'reporter_email': 'Needed so our team can follow up, even if you submit anonymously. '
                              'Never shown publicly.',
            'anonymous': 'Your name and phone number are not needed. We still need your email so our '
                         'team can follow up, but it is never shown publicly.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
            raise ValidationError("The amount lost cannot be negative.")
        return amount

    def clean_description(self):
        desc = self.cleaned_data.get('description')
        if len(desc) < 20:
            raise ValidationError("Please provide a more detailed description (at least 20 characters).")
        return desc

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount_lost')
        currency = cleaned_data.get('currency')

        if amount and amount > 0 and not currency:
            self.add_error('currency', "Please select a currency for the reported loss.")

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
                self.add_error('description', "A very similar scam report has already been submitted.")
                break

        return cleaned_data
