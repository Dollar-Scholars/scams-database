from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator
from django.core.exceptions import ValidationError
from datetime import date
from django.utils.translation import gettext_lazy as _, pgettext_lazy

# Choice labels are translated (gettext_lazy), so they show in the page's language.
CHANNEL_CHOICES = [
    ("phone", _("Phone call")),
    ("sms", _("SMS")),
    ("email", _("Email")),
    ("mail", _("Mail")),
    ("social", _("Social media")),
    ("messaging", _("Messaging app")),
    ("website", _("Website / ad")),
    ("in_person", _("In person approach")),
    ("other", _("Other channel")),
]

TYPE_CHOICES = [
    ("financial", _("Financial transfer scams")),
    ("identity", _("Identity and impersonation scams")),
    ("investment", _("Investment and wealth scams")),
    ("other", _("Other scams")),
]

# The report form shows these with Babel's currency names in the page's language (forms.py).
CURRENCY_CHOICES = [
    ("USD", _("USD — US Dollar")), ("EUR", _("EUR — Euro")), ("GBP", _("GBP — British Pound")),
    ("AUD", _("AUD — Australian Dollar")), ("CAD", _("CAD — Canadian Dollar")), ("INR", _("INR — Indian Rupee")),
    ("MXN", _("MXN — Mexican Peso")),
    ("NGN", _("NGN — Nigerian Naira")), ("ZAR", _("ZAR — South African Rand")), ("BRL", _("BRL — Brazilian Real")),
    ("JPY", _("JPY — Japanese Yen")), ("CNY", _("CNY — Chinese Yuan")), ("Other", pgettext_lazy("currency", "Other")),
]

# English names. The report form shows Babel's names in the page's language instead
# (forms.py), so these are not marked for translation.
COUNTRY_CHOICES = [
    ('AF', 'Afghanistan'), ('AL', 'Albania'), ('DZ', 'Algeria'), ('AS', 'American Samoa'), ('AD', 'Andorra'),
    ('AO', 'Angola'), ('AI', 'Anguilla'), ('AQ', 'Antarctica'), ('AG', 'Antigua and Barbuda'), ('AR', 'Argentina'),
    ('AM', 'Armenia'), ('AW', 'Aruba'), ('AU', 'Australia'), ('AT', 'Austria'), ('AZ', 'Azerbaijan'),
    ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'), ('BY', 'Belarus'),
    ('BE', 'Belgium'), ('BZ', 'Belize'), ('BJ', 'Benin'), ('BM', 'Bermuda'), ('BT', 'Bhutan'),
    ('BO', 'Bolivia'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BR', 'Brazil'), ('BN', 'Brunei'),
    ('BG', 'Bulgaria'), ('BF', 'Burkina Faso'), ('BI', 'Burundi'), ('KH', 'Cambodia'), ('CM', 'Cameroon'),
    ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('TD', 'Chad'),
    ('CL', 'Chile'), ('CN', 'China'), ('CO', 'Colombia'), ('KM', 'Comoros'), ('CG', 'Congo'), ('CR', 'Costa Rica'),
    ('HR', 'Croatia'), ('CU', 'Cuba'), ('CY', 'Cyprus'), ('CZ', 'Czech Republic'), ('DK', 'Denmark'),
    ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'), ('EG', 'Egypt'),
    ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ER', 'Eritrea'), ('EE', 'Estonia'), ('ET', 'Ethiopia'),
    ('FJ', 'Fiji'), ('FI', 'Finland'), ('FR', 'France'), ('GA', 'Gabon'), ('GM', 'Gambia'), ('GE', 'Georgia'),
    ('DE', 'Germany'), ('GH', 'Ghana'), ('GR', 'Greece'), ('GD', 'Grenada'), ('GU', 'Guam'), ('GT', 'Guatemala'),
    ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'), ('GY', 'Guyana'), ('HT', 'Haiti'), ('HN', 'Honduras'),
    ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'),
    ('IR', 'Iran'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IL', 'Israel'), ('IT', 'Italy'), ('JM', 'Jamaica'),
    ('JP', 'Japan'), ('JO', 'Jordan'), ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'),
    ('KP', 'Korea, North'), ('KR', 'Korea, South'), ('KW', 'Kuwait'), ('KG', 'Kyrgyzstan'), ('LA', 'Laos'),
    ('LV', 'Latvia'), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LR', 'Liberia'), ('LY', 'Libya'),
    ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'), ('MO', 'Macao'), ('MK', 'Macedonia'),
    ('MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'),
    ('MT', 'Malta'), ('MH', 'Marshall Islands'), ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('MX', 'Mexico'),
    ('FM', 'Micronesia'), ('MD', 'Moldova'), ('MC', 'Monaco'), ('MN', 'Mongolia'), ('MS', 'Montserrat'),
    ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('MM', 'Myanmar'), ('NA', 'Namibia'), ('NR', 'Nauru'),
    ('NP', 'Nepal'), ('NL', 'Netherlands'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'),
    ('NG', 'Nigeria'), ('NO', 'Norway'), ('OM', 'Oman'), ('PK', 'Pakistan'), ('PW', 'Palau'),
    ('PS', 'Palestine'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'),
    ('PH', 'Philippines'), ('PL', 'Poland'), ('PT', 'Portugal'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'),
    ('RO', 'Romania'), ('RU', 'Russia'), ('RW', 'Rwanda'), ('KN', 'Saint Kitts and Nevis'), ('LC', 'Saint Lucia'),
    ('VC', 'Saint Vincent'), ('WS', 'Samoa'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'),
    ('SN', 'Senegal'), ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'),
    ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SB', 'Solomon Islands'), ('SO', 'Somalia'), ('ZA', 'South Africa'),
    ('ES', 'Spain'), ('LK', 'Sri Lanka'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SZ', 'Swaziland'),
    ('SE', 'Sweden'), ('CH', 'Switzerland'), ('SY', 'Syria'), ('TW', 'Taiwan'), ('TJ', 'Tajikistan'),
    ('TZ', 'Tanzania'), ('TH', 'Thailand'), ('TG', 'Togo'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'),
    ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('UG', 'Uganda'), ('UA', 'Ukraine'),
    ('AE', 'United Arab Emirates'), ('GB', 'United Kingdom'), ('US', 'United States'), ('UY', 'Uruguay'),
    ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'), ('VA', 'Vatican City'), ('VE', 'Venezuela'), ('VN', 'Vietnam'),
    ('YE', 'Yemen'), ('ZM', 'Zambia'), ('ZW', 'Zimbabwe'),
]

def validate_not_future(value):
    if value and value > date.today():
        raise ValidationError(_("The date cannot be in the future."))

class Scam(models.Model):
    title = models.CharField(max_length=255)
    date_occurred = models.DateField(validators=[validate_not_future], null=True, blank=True)
    amount_lost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, blank=True)
    platform = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    phishing = models.BooleanField(null=True, blank=True)
    contact_method = models.CharField(max_length=100,choices=CHANNEL_CHOICES, default="undefined")
    scam_type = models.CharField(max_length=100,choices=TYPE_CHOICES, default="undefined")
    url_or_contact = models.CharField(max_length=255, blank=True)
    severity = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    scammer_name = models.CharField(max_length=255, blank=True)
    scammer_contact = models.CharField(max_length=255, blank=True)

    reporter_name = models.CharField(max_length=255, blank=True)
    reporter_email = models.EmailField(validators=[EmailValidator()])
    reporter_phone = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES, blank=True)
    anonymous = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"{self.title} ({self.reporter_email})"