from django import forms
from .models import Scam

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
            'title': forms.TextInput(attrs={'id': 'id_title'}),
            'scam_type': forms.Select(attrs={'id': 'id_scam_type'}),
            'date_occurred': forms.DateInput(attrs={'type': 'date', 'id': 'id_date_occurred'}),
            'amount_lost': forms.NumberInput(attrs={'id': 'id_amount_lost', 'step': '0.01'}),
            'currency': forms.Select(attrs={'id': 'id_currency'}),
            'platform': forms.TextInput(attrs={'id': 'id_platform'}),
            'description': forms.Textarea(attrs={'id': 'id_description', 'rows': 4}),
            'severity': forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '5', 'id': 'sevRange', 'oninput': 'updateSeverity(this.value)'}),
            'scammer_name': forms.TextInput(attrs={'id': 'id_scammer_name'}),
            'scammer_contact': forms.TextInput(attrs={'id': 'id_scammer_contact'}),
            'contact_method': forms.RadioSelect(attrs={'id': 'contactMethod'}),
            'reporter_name': forms.TextInput(attrs={'id': 'id_reporter_name'}),
            'reporter_email': forms.EmailInput(attrs={'id': 'id_reporter_email'}),
            'reporter_phone': forms.TextInput(attrs={'id': 'id_reporter_phone'}),
            'country': forms.Select(attrs={'id': 'id_country'}),
            'anonymous': forms.CheckboxInput(attrs={'id': 'id_anonymous'}),
        }