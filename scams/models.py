from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

SCAM_CHANNELS = [
    ("phone", "Phone call"),
    ("sms", "SMS"),
    ("email", "Email"),
    ("mail","Mail"),
    ("social", "Social media"),
    ("messaging", "Messaging app"),
    ("website", "Website / ad"),
    ("in_person", "In person approach"),
    ("other","Other channel"),
    ]

SCAM_TYPES = [
    ("financial", "Financial transfer scams"),
    ("identity", "Identity and impersonation scams"),
    ("investment", "Investment and wealth scams"),
    ("other", "Other scams"),
    ]



CURRENCY_CHOICES = [
    ("USD", "USD — US Dollar"),
    ("EUR", "EUR — Euro"),
    ("GBP", "GBP — British Pound"),
    ("AUD", "AUD — Australian Dollar"),
    ("CAD", "CAD — Canadian Dollar"),
    ("INR", "INR — Indian Rupee"),
    ("NGN", "NGN — Nigerian Naira"),
    ("ZAR", "ZAR — South African Rand"),
    ("BRL", "BRL — Brazilian Real"),
    ("JPY", "JPY — Japanese Yen"),
    ("CNY", "CNY — Chinese Yuan"),
    ("Other", "Other"),
]

class Scam(models.Model):
    # Incident Details
    title = models.CharField(max_length=255)
    scam_type = models.CharField(max_length=100, choices=SCAM_TYPES)
    date_occurred = models.DateField(null=True, blank=True)
    amount_lost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, blank=True)
    platform = models.CharField(max_length=100, blank=True) # "Platform / channel" field
    description = models.TextField()
    phishing = models.BooleanField(null=True, blank=True)
    contact_method = models.CharField(max_length=100,choices=SCAM_CHANNELS, default="undefined")
    scam_type = models.CharField(max_length=100,choices=SCAM_TYPES, default="undefined")
    date_seen = models.DateField()
    url_or_contact = models.CharField(max_length=255, blank=True)
    severity = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # Scammer Information
    scammer_name = models.CharField(max_length=255, blank=True)
    scammer_contact = models.CharField(max_length=255, blank=True) # Phone/Email/Web
    contact_method = models.CharField(max_length=100, choices=SCAM_CHANNELS)

    # Reporter Information
    reporter_name = models.CharField(max_length=255, blank=True)
    reporter_email = models.EmailField(default="")
    reporter_phone = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)
    anonymous = models.BooleanField(default=False)

    # Internal Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"{self.title} ({self.reporter_email})"