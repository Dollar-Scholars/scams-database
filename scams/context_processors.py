from django.conf import settings
from django.urls import translate_url


def site_embeds(request):
    """The main site's header/footer location, and this page's address in every language."""
    path = request.get_full_path()
    return {
        'DS_SITE_URL': settings.DS_SITE_URL,
        # <link rel="alternate" hreflang> for search engines, and for the shared header's
        # language picker, which links to these instead of the main site's home pages.
        'LANGUAGE_ALTERNATES': [
            (code, request.build_absolute_uri(translate_url(path, code)))
            for code, _name in settings.LANGUAGES
        ],
    }
