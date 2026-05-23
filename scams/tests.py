from django.test import TestCase

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from .models import Scam
from .forms import ScamReportForm

class ScamDuplicateCheckTest(TestCase):

    def setUp(self):
        self.valid_form_data = {
            'title': 'Fake Crypto Investment',
            'scam_type': 'investment',
            'date_occurred': '2026-05-20',
            'amount_lost': 0,
            'currency': '',
            'platform': 'WhatsApp',
            'description': 'I was contacted by someone promising huge returns on a new trading platform.',
            'severity': 3,
            'scammer_name': 'Crypto King',
            'scammer_contact': '@cryptoking',
            'contact_method': 'messaging',
            'reporter_name': 'Test User',
            'reporter_email': 'test@example.com',
            'reporter_phone': '555-0199',
            'country': 'GB',
            'anonymous': False
        }

    def test_duplicate_blocked(self):
        """Should block similar descriptions"""
        Scam.objects.create(
            title="Fake Crypto App",
            description="I was contacted by someone promising huge returns on a new trading platform.",
        )

        data = self.valid_form_data.copy()
        data['description'] = "Contacted by someone promising huge returns on a new crypto trading platform."
        
        form = ScamReportForm(data=data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)
        self.assertEqual(
            form.errors['description'][0], 
            "A very similar scam report has already been submitted."
        )

    def test_nonduplicate_allowed(self):
        """Test that a different description is allowed."""
        Scam.objects.create(
            title="Fake Crypto App",
            description="I was contacted by someone promising huge returns on a new trading platform.",
        )

        data = self.valid_form_data.copy()
        data['description'] = "I bought concert tickets on Facebook Marketplace and the seller blocked me."
        
        form = ScamReportForm(data=data)
        
        
        print(form.errors)
        self.assertTrue(form.is_valid())
