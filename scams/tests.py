from django.test import TestCase
from .models import Scam
from .forms import ScamReportForm

class ScamDuplicateCheckTest(TestCase):

    def setUp(self):
        self.valid_form_data = {
            'title': 'Report Submission',
            'scam_type': 'investment',
            'date_occurred': '2026-05-20',
            'amount_lost': 0,
            'currency': '',
            'platform': 'WhatsApp',
            'severity': 3,
            'scammer_name': 'Unknown',
            'scammer_contact': '@unknown',
            'contact_method': 'messaging',
            'reporter_name': 'Test User',
            'reporter_email': 'test@example.com',
            'reporter_phone': '555-0199',
            'country': 'GB',
            'anonymous': False
        }

        self.reports = [
            # Short reports
            {
                "scenario_name": "Similar Short - Minor wording variation",
                "existing_desc": "I was contacted by someone promising huge returns on a new trading platform.",
                "new_desc": "Contacted by someone promising huge returns on a new crypto trading platform.",
                "is_duplicate": True,
            },
            {
                "scenario_name": "Similar Short - Phishing SMS variation",
                "existing_desc": "Got a text from Royal Mail about a missed parcel. Clicked the link and it asked for a redelivery fee.",
                "new_desc": "Received an SMS claiming to be Royal Mail saying I missed a delivery. The link demanded payment to reschedule.",
                "is_duplicate": True,
            },
            {
                "scenario_name": "Dissimilar Short - Completely different subject matter",
                "existing_desc": "I was contacted by someone promising huge returns on a new trading platform.",
                "new_desc": "I bought concert tickets on Facebook Marketplace and the seller blocked me.",
                "is_duplicate": False,
            },
            {
                "scenario_name": "Dissimilar Short - Same platform, different scam mechanics",
                "existing_desc": "Someone on WhatsApp pretended to be my daughter needing money for a broken phone.",
                "new_desc": "Someone on WhatsApp offered me a part-time job liking YouTube videos for crypto.",
                "is_duplicate": False,
            },
            
            # Long reports
            {
                "scenario_name": "Similar Long - Pet scam with varied phrasing and formatting",
                "existing_desc": (
                    'I am reporting a fraudulent website called "Premier Frenchie Pups" (premierfrenchiepups.com). '
                    'On October 14th, 2023, I contacted the seller, who identified himself as James Miller, about '
                    'purchasing a female French Bulldog puppy named Luna. We communicated via email and text message '
                    '(number 555-019-8472). He requested a payment of $1,200 for the puppy, which I transferred using '
                    'Zelle. Two days later, on October 16th, I received an email from a supposed third-party logistics '
                    'company called "AeroPet Transit." They claimed I needed to pay a $650 refundable insurance deposit '
                    'for a temperature-controlled crate before the puppy could board the flight. When I refused to pay '
                    'this unexpected fee and requested a refund from James, he stopped responding, blocked my number, '
                    'and the website was taken offline within 24 hours.'
                ),
                "new_desc": (
                    'Fraud report regarding Premier French Pups (premierfrenchiepups.com). Contacted the breeder, '
                    'James Millar, on 10/14/2023 about buying a female frenchie pup (Luna). Communicated through email '
                    'and texting at 5550198472. He asked for $1200 via Zelle for the dog, which was paid in full. On '
                    'Oct 16, got an email from a transport company named Aero Pet Transit. They said a $650.00 refundable '
                    'crate insurance fee was required for temperature control before shipping. I declined paying the extra '
                    'money and demanded my original payment back from James. The seller immediately ghosted me, blocked '
                    'my phone, and their website went dead the next day.'
                ),
                "is_duplicate": True,
            },
            {
                "scenario_name": "Similar Long - Tech support scam with structural changes",
                "existing_desc": (
                    'I received a popup on my computer stating that my Windows defender had expired and my computer '
                    'was locked due to a virus. It told me to call Microsoft Support immediately at 1-800-123-4567. '
                    'When I called, a man with a foreign accent told me he needed remote access to fix it. He installed '
                    'AnyDesk and then showed me fake errors, claiming I needed to pay $500 in Target gift cards to '
                    'remove the hackers from my network.'
                ),
                "new_desc": (
                    'A warning popped up on my screen saying my PC was infected with malware and Windows Defender was '
                    'disabled. The alert gave a phone number (800-123-4567) to reach Microsoft. I dialed the number '
                    'and spoke to a representative who said they needed to remote into my machine via AnyDesk. After '
                    'connecting, he pulled up some scary looking black screens and demanded $500 paid via Target gift '
                    'cards to clean the system.'
                ),
                "is_duplicate": True,
            },
            {
                "scenario_name": "Dissimilar Long - Two completely different long scams",
                "existing_desc": (
                    'I received a popup on my computer stating that my Windows defender had expired and my computer '
                    'was locked due to a virus. It told me to call Microsoft Support immediately at 1-800-123-4567. '
                    'When I called, a man with a foreign accent told me he needed remote access to fix it. He installed '
                    'AnyDesk and then showed me fake errors, claiming I needed to pay $500 in Target gift cards to '
                    'remove the hackers from my network.'
                ),
                "new_desc": (
                    'I am reporting a fraudulent website called "Premier Frenchie Pups" (premierfrenchiepups.com). '
                    'On October 14th, 2023, I contacted the seller, who identified himself as James Miller, about '
                    'purchasing a female French Bulldog puppy named Luna. We communicated via email and text message '
                    '(number 555-019-8472). He requested a payment of $1,200 for the puppy, which I transferred using '
                    'Zelle.'
                ),
                "is_duplicate": False,
            },
            {
                "scenario_name": "Dissimilar Mixed - Long detailed report vs short unrelated report",
                "existing_desc": (
                    'I am reporting a fraudulent website called "Premier Frenchie Pups" (premierfrenchiepups.com). '
                    'On October 14th, 2023, I contacted the seller, who identified himself as James Miller, about '
                    'purchasing a female French Bulldog puppy named Luna. We communicated via email and text message '
                    '(number 555-019-8472). He requested a payment of $1,200 for the puppy, which I transferred using '
                    'Zelle.'
                ),
                "new_desc": "Someone on WhatsApp offered me a part-time job liking YouTube videos for crypto.",
                "is_duplicate": False,
            }
        ]

    def test_duplicate_descriptions(self):
        """Test fuzzy string matching across various similar and dissimilar descriptions."""
        
        for case in self.reports:
            with self.subTest(msg=case["scenario_name"]):
                Scam.objects.all().delete()
                
                Scam.objects.create(
                    title="Seeded DB Report",
                    description=case["existing_desc"],
                )
                
                data = self.valid_form_data.copy()
                data['description'] = case["new_desc"]
                
                form = ScamReportForm(data=data)
                is_valid = form.is_valid()
                
                if case["is_duplicate"]:
                    self.assertFalse(
                        is_valid, 
                        f"Expected form to be blocked as a duplicate, but it was accepted."
                    )
                    self.assertIn('description', form.errors)
                    self.assertEqual(
                        form.errors['description'][0], 
                        "A very similar scam report has already been submitted."
                    )
                else:
                    self.assertTrue(
                        is_valid, 
                        f"Expected form to be accepted, but got errors: {form.errors}"
                    )
