from django.contrib import admin
from .models import Scam


# Show real columns in the admin list (the default single __str__ column
# looks sortable in Django 5.2 but can't be sorted).
@admin.register(Scam)
class ScamAdmin(admin.ModelAdmin):
    list_display = ('title', 'scam_type', 'contact_method', 'country', 'status', 'created_at')
    list_filter = ('status', 'scam_type', 'contact_method')
    search_fields = ('title', 'description', 'platform', 'scammer_name', 'scammer_contact')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
