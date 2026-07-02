from django import forms
from .models import Scam
from django.core.exceptions import ValidationError
from thefuzz import fuzz
from django.utils import timezone
from datetime import timedelta

SMALL_REPORT_LENGTH = 100

class ScamReportForm(forms.ModelForm):
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
            'amount_lost': forms.NumberInput(attrs={'id': 'id_amount_lost', 'step': '0.01', 'min': '0'}),
            'currency': forms.Select(attrs={'id': 'id_currency'}),
            'platform': forms.TextInput(attrs={'id': 'id_platform'}),
            'description': forms.Textarea(
                attrs={'id': 'id_description', 'rows': 4, 'placeholder': 'Provide as much detail as possible...'}),
            'severity': forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '5', 'id': 'sevRange',
                                                 'oninput': 'updateSeverity(this.value)'}),
            'scammer_name': forms.TextInput(attrs={'id': 'id_scammer_name'}),
            'scammer_contact': forms.TextInput(attrs={'id': 'id_scammer_contact'}),
            'contact_method': forms.RadioSelect(attrs={'id': 'contactMethod'}),
            'reporter_name': forms.TextInput(attrs={'id': 'id_reporter_name'}),
            'reporter_email': forms.EmailInput(attrs={'id': 'id_reporter_email'}),
            'reporter_phone': forms.TextInput(attrs={'id': 'id_reporter_phone'}),
            'country': forms.Select(attrs={'id': 'id_country'}),
            'anonymous': forms.CheckboxInput(attrs={'id': 'id_anonymous'}),
        }

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

        description = cleaned_data.get('description', '')
        one_day_ago = timezone.now() - timedelta(days=1)

        recent_scams = Scam.objects.filter(created_at__gte=one_day_ago)

        for scam in recent_scams:
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
