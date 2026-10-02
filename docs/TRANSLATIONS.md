# Translations

ScamDB is offered in the same 44 languages as dollarscholars.org (`scams/languages.py`),
so the shared header's language picker works on both sites. English is the source; every
other language lives under its own prefix: `/es/dashboard/`, `/ar/`, `/zh-hans/...`.

**ScamDB's translations are made and reviewed on dollarscholars.org**, together with the
main site's own: machine translated there with Azure AI Translator, then checked by
volunteers and staff in its admin and volunteer portal, where ScamDB's texts are listed as
"ScamDB wording" (portal filter: *ScamDB*). Nothing is translated in this repository, and
it has no translation keys.

```
ScamDB repo                        dollarscholars.org                       ScamDB server
translation_sources.json  ──────>  sync_translations (reads it from GitHub)
 (English, committed)              machine_translate --kind scamdb (Azure)
                                   review in the admin / volunteer portal
                                   /translations/scamdb.json  ──────────>  fetch_translations
                                                                            (when it starts)
```

## Where the text lives

| What | Where |
|---|---|
| Page text, labels, messages | templates (`{% translate %}`, `{% blocktranslate %}`) and Python (`gettext`, `pgettext`) |
| Text the page scripts show | rendered into the page by the templates, so it is translated the same way |
| Country, currency and month names | Babel (CLDR data), already in every language |
| The English list for dollarscholars.org | `translation_sources.json` (committed) |
| The translations | downloaded into `locale/<language>/LC_MESSAGES/django.mo` (not committed) |

`scams/locale/` holds empty catalogs for Amharic, Haitian Creole, Tagalog, Yoruba and
Zulu: Django serves a language's pages only if it has a catalog for it, and it ships none
for those five.

## After changing or adding English text

```bash
python manage.py export_translation_sources   # rewrite translation_sources.json
python manage.py test scams
```

Commit `translation_sources.json` with the change (a test fails until you do). Once it is
on `main`, the new text reaches dollarscholars.org the next time it deploys, or straight
away when someone runs these on its server:

```bash
.venv/bin/python manage.py sync_translations --scamdb-only
.venv/bin/python manage.py machine_translate --kind scamdb
```

Until then the new text shows in English in the other languages.

**No plurals.** dollarscholars.org's translations have no plural forms, so `ngettext` and
`{% plural %}` are refused (`export_translation_sources` names them). Word things so the
number stands apart: "Reports: %(count)s", "Topics reviewed: %(reviewed)s of %(total)s",
"No date given: %(count)s".

Keep each placeholder (`%(name)s`, or `{{ name }}` in a template) in the sentence it
belongs to: a translator can reorder words but not split a sentence across two texts.

## Getting the latest translations

ScamDB downloads them from `<DS_SITE_URL>/translations/scamdb.json` (or
`DS_TRANSLATIONS_URL`) with `python manage.py fetch_translations`:

- when the image is built (`deploy/deploy.sh`), and
- every time the container starts, so `docker restart scamdb-app` brings in translations
  reviewed since the last deploy.

If the download fails, the translations already in the image stay and ScamDB starts
anyway; any text with no translation shows in English. A translation whose placeholders
don't match the English is left out, so it can't break a page.

On your own computer, run `python manage.py fetch_translations` to see the pages
translated (`locale/` is ignored by git). Set `DS_TRANSLATIONS_URL=` (empty) to stay in
English.

## Reviewing a translation

On dollarscholars.org: the admin's Translations screens (filter by kind:
*ScamDB wording*), or the volunteer portal's Translate pages (*Part of the site: ScamDB*). A
reviewed translation is never replaced by machine translation. It reaches ScamDB the next
time ScamDB starts.
