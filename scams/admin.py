from django.contrib import admin
from .models import Scam

# This line tells Django to include your model in the admin site
admin.site.register(Scam)