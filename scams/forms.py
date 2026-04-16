from django import forms
from .models import Scam
from django.core.exceptions import ValidationError


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

        return cleaned_data