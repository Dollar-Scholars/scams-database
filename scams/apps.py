from django.apps import AppConfig
from django.utils import translation


def _deactivate_language(**kwargs):
    translation.deactivate()


class ScamsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scams'

    def ready(self):
        # Django has no locale info for a few of our languages (Amharic, Haitian Creole, ...);
        # register it like dollarscholars.org does, or get_language_info() fails for them.
        from django.conf.locale import LANG_INFO

        from .languages import EXTRA_LANG_INFO

        for code, info in EXTRA_LANG_INFO.items():
            LANG_INFO.setdefault(code, info)

        # LocaleMiddleware activates the request's language (/es/...) on the thread and leaves it
        # active afterwards. Harmless for the server, which sets it per request, but it leaks into
        # whatever runs next on the thread (in tests: the next test). Reset it when a request ends.
        from django.core.signals import request_finished

        request_finished.connect(_deactivate_language, dispatch_uid='scams-reset-language')
