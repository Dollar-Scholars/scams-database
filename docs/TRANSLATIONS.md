# Translations

ScamDB is offered in the same 44 languages as dollarscholars.org (`scams/languages.py`),
so the shared header's language picker works on both sites. English is the source; every
other language lives under its own prefix: `/es/dashboard/`, `/ar/`, `/zh-hans/...`.

The translations are machine-made with **Azure AI Translator** (the same service the main
site uses) and are marked in the catalogs as *"Machine translated (Azure Translator), not
reviewed"* until a person checks them.

## Where the text lives

| What | Where |
|---|---|
| Page text, labels, messages | templates (`{% translate %}`, `{% blocktranslate %}`) and Python (`gettext`) |
| Text the page scripts show | rendered into the page by the templates, so it is translated the same way |
| Country and currency names | Babel (CLDR data), already in every language |
| Translations | `locale/<language>/LC_MESSAGES/django.po` (edit these) and `django.mo` (compiled) |

## After changing or adding English text

Run from the repo root with Git Bash (it ships the gettext tools Django needs) or on
macOS/Linux with gettext installed:

```bash
python manage.py makemessages --all --no-obsolete   # collect the new English text
python manage.py translate_po --dry-run              # how many characters would be sent
python manage.py translate_po                        # machine-translate what is missing
python manage.py compilemessages                     # build the .mo files the site reads
python manage.py test scams
```

`translate_po` needs `AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION` in `.env` (see
`.env.example`). It only sends entries that have no translation yet, so a translation
someone has reviewed or corrected is never replaced, and Azure's free tier (2 million
characters a month, shared with the main site) is spent only on new text. It leaves out any
translation that lost a placeholder such as `%(count)s`, so a page can never break.
`translate_po -l es -l fr` does just some languages.

Commit the `.po` and `.mo` files together.

## Reviewing a translation

Open `locale/<language>/LC_MESSAGES/django.po`, correct the `msgstr` lines, remove the
`#. Machine translated (Azure Translator), not reviewed` comment above each entry you
checked, then run `python manage.py compilemessages` and open a pull request.
