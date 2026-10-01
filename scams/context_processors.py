from django.conf import settings


def site_embeds(request):
    """Where base.html loads the main Dollar Scholars site's header and footer from."""
    return {'DS_SITE_URL': settings.DS_SITE_URL}
