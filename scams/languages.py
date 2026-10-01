"""Languages ScamDB is offered in: the same as dollarscholars.org's, so the shared header's
language picker works on both (copied from its translations/languages.py; keep in step).

This module must stay importable from settings.py, so it has no Django imports.
"""

# (code used in URLs and the database, English name, name in that language)
SITE_LANGUAGES = [
    ("en", "English", "English"),
    ("am", "Amharic", "አማርኛ"),
    ("ar", "Arabic", "العربية"),
    ("bn", "Bengali", "বাংলা"),
    ("cs", "Czech", "Čeština"),
    ("da", "Danish", "Dansk"),
    ("de", "German", "Deutsch"),
    ("el", "Greek", "Ελληνικά"),
    ("es", "Spanish", "Español"),
    ("es-mx", "Spanish (Mexico)", "Español de México"),
    ("fa", "Persian", "فارسی"),
    ("fi", "Finnish", "Suomi"),
    ("fr", "French", "Français"),
    ("he", "Hebrew", "עברית"),
    ("hi", "Hindi", "हिन्दी"),
    ("hr", "Croatian", "Hrvatski"),
    ("ht", "Haitian Creole", "Kreyòl ayisyen"),
    ("hu", "Hungarian", "Magyar"),
    ("id", "Indonesian", "Bahasa Indonesia"),
    ("ig", "Igbo", "Asụsụ Igbo"),
    ("it", "Italian", "Italiano"),
    ("ja", "Japanese", "日本語"),
    ("ko", "Korean", "한국어"),
    ("ms", "Malay", "Bahasa Melayu"),
    ("nl", "Dutch", "Nederlands"),
    ("pl", "Polish", "Polski"),
    ("pt", "Portuguese", "Português"),
    ("ro", "Romanian", "Română"),
    ("ru", "Russian", "Русский"),
    ("sk", "Slovak", "Slovenčina"),
    ("sl", "Slovenian", "Slovenščina"),
    ("sq", "Albanian", "Shqip"),
    ("sv", "Swedish", "Svenska"),
    ("sw", "Swahili", "Kiswahili"),
    ("th", "Thai", "ภาษาไทย"),
    ("tl", "Tagalog", "Tagalog"),
    ("tr", "Turkish", "Türkçe"),
    ("uk", "Ukrainian", "Українська"),
    ("ur", "Urdu", "اردو"),
    ("vi", "Vietnamese", "Tiếng Việt"),
    ("yo", "Yoruba", "Yorùbá"),
    ("zh-hans", "Chinese (Simplified)", "简体中文"),
    ("zh-hant", "Chinese (Traditional)", "繁體中文"),
    ("zu", "Zulu", "isiZulu"),
]

SOURCE_LANGUAGE = "en"

# For settings.LANGUAGES.
LANGUAGES = [(code, english) for code, english, _native in SITE_LANGUAGES]

# Every language except the English source text.
TARGET_LANGUAGES = [code for code, _e, _n in SITE_LANGUAGES if code != SOURCE_LANGUAGE]

# Site language code -> code the machine translation service expects.
# Everything matches except Chinese, which Django calls "zh-hans"/"zh-hant".
LANGUAGE_MAP = {code: code for code in TARGET_LANGUAGES}
# Mexican Spanish is its own language to Azure, plain Spanish to Google.
LANGUAGE_MAP["es-mx"] = "es"
LANGUAGE_MAP["zh-hans"] = "zh-CN"
LANGUAGE_MAP["zh-hant"] = "zh-TW"

# Django doesn't ship locale info for these, so we register it on startup.
EXTRA_LANG_INFO = {
    "am": {"bidi": False, "code": "am", "name": "Amharic", "name_local": "አማርኛ"},
    "ht": {"bidi": False, "code": "ht", "name": "Haitian Creole",
           "name_local": "Kreyòl ayisyen"},
    "tl": {"bidi": False, "code": "tl", "name": "Tagalog", "name_local": "Tagalog"},
    "yo": {"bidi": False, "code": "yo", "name": "Yoruba", "name_local": "Yorùbá"},
    "zu": {"bidi": False, "code": "zu", "name": "Zulu", "name_local": "isiZulu"},
}
