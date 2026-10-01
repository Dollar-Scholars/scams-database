"""Fill ScamDB's translation catalogs (locale/<lang>/LC_MESSAGES/django.po) by machine.

Uses Azure AI Translator, like dollarscholars.org (its translations/machine.py): the same
language codes, pacing and placeholder protection. Only entries with no translation yet
are sent, so a translation someone has reviewed or corrected is never replaced.

Backends:
  azure  Azure AI Translator. Needs AZURE_TRANSLATOR_KEY (+ AZURE_TRANSLATOR_REGION, and
         AZURE_TRANSLATOR_ENDPOINT for a resource with its own custom domain).
  dummy  Returns "[es] English text". For tests and trying the workflow.
"""
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque

HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>|&[a-zA-Z#0-9]+;")
# Django placeholders (%(name)s from {% blocktranslate %}, %s) and literal %%.
PROTECT_RE = re.compile(r"%\(\w+\)[sdif]|%[sdif]|%%")
UNPROTECT_RE = re.compile(r'<span\s+class="notranslate"\s*>\s*(.*?)\s*</span>', re.S)

MAX_ITEMS_PER_REQUEST = 100
MAX_CHARS_PER_REQUEST = 20000
MACHINE_COMMENT = "Machine translated (Azure Translator), not reviewed"


class MachineTranslationError(Exception):
    pass


class DummyBackend:
    name = "dummy"

    def translate(self, texts, target):
        return [f"[{target}] {text}" for text in texts]


class AzureBackend:
    """Azure AI Translator, Text Translation API v3 (always sent as HTML, see _protect)."""

    name = "azure"
    default_endpoint = "https://api.cognitive.microsofttranslator.com"
    # Azure's codes differ from ours for these.
    language_map = {"zh-hans": "zh-Hans", "zh-hant": "zh-Hant", "es-mx": "es-MX", "tl": "fil"}
    chars_per_minute = 30000
    max_retries = 6

    def __init__(self):
        self.key = os.getenv("AZURE_TRANSLATOR_KEY", "")
        self.region = os.getenv("AZURE_TRANSLATOR_REGION", "")
        self.endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", self.default_endpoint).rstrip("/")
        if not self.key:
            raise MachineTranslationError(
                "Set AZURE_TRANSLATOR_KEY (and AZURE_TRANSLATOR_REGION, e.g. eastus) in the "
                "environment or .env to use Azure Translator."
            )
        self._sent = deque()

    def _url(self, query):
        # The global endpoint serves the API at its root; a custom-domain resource under
        # /translator/text/v3.0/ (same rule as dollarscholars.org).
        host = urllib.parse.urlsplit(self.endpoint).hostname or ""
        default_host = urllib.parse.urlsplit(self.default_endpoint).hostname
        if host == default_host or self.endpoint.endswith("/translator/text/v3.0"):
            return f"{self.endpoint}/translate?{query}"
        return f"{self.endpoint}/translator/text/v3.0/translate?{query}"

    def _pace(self, characters):
        while True:
            now = time.monotonic()
            while self._sent and now - self._sent[0][0] > 60:
                self._sent.popleft()
            used = sum(chars for _t, chars in self._sent)
            if not self._sent or used + characters <= self.chars_per_minute:
                break
            time.sleep(max(0.5, 60 - (now - self._sent[0][0])))
        self._sent.append((time.monotonic(), characters))

    def translate(self, texts, target):
        query = urllib.parse.urlencode({
            "api-version": "3.0", "from": "en",
            "to": self.language_map.get(target, target), "textType": "html",
        })
        body = json.dumps([{"Text": text} for text in texts]).encode("utf-8")
        headers = {"Ocp-Apim-Subscription-Key": self.key,
                   "Content-Type": "application/json; charset=UTF-8"}
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region
        for attempt in range(self.max_retries + 1):
            self._pace(sum(len(text) for text in texts))
            request = urllib.request.Request(self._url(query), data=body, headers=headers,
                                             method="POST")
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                return [item["translations"][0]["text"] for item in payload]
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:500]
                if exc.code in (429, 500, 503) and attempt < self.max_retries:
                    wait = exc.headers.get("Retry-After") if exc.headers else None
                    time.sleep(float(wait) if wait and wait.isdigit() else 2 ** (attempt + 2))
                    continue
                if exc.code == 401:
                    detail = "the key or region is wrong. " + detail
                elif exc.code == 403:
                    detail = "the monthly allowance may be used up. " + detail
                raise MachineTranslationError(f"Azure Translator error {exc.code}: {detail}")
            except urllib.error.URLError as exc:
                raise MachineTranslationError(f"Could not reach Azure Translator: {exc.reason}")
        raise MachineTranslationError("Azure Translator kept rate-limiting; try again later.")


BACKENDS = {"azure": AzureBackend, "dummy": DummyBackend}


def get_backend(name):
    try:
        return BACKENDS[name]()
    except KeyError:
        raise MachineTranslationError(f"Unknown backend {name!r}. Choose from: {', '.join(BACKENDS)}")


def _protect(text):
    """Wrap placeholders so the translator leaves them alone (not inside tags)."""
    def wrap(part):
        return PROTECT_RE.sub(lambda m: f'<span class="notranslate">{m.group(0)}</span>', part)

    parts = HTML_TAG_RE.split(text)
    tags = HTML_TAG_RE.findall(text)
    return "".join(wrap(part) + (tags[i] if i < len(tags) else "") for i, part in enumerate(parts))


def _finish(source, translated):
    translated = UNPROTECT_RE.sub(lambda m: html.unescape(m.group(1)), translated)
    if not HTML_TAG_RE.search(source):
        # Sent as HTML, so the service may have escaped & < > in plain text.
        translated = html.unescape(translated)
    # Keep the source's leading/trailing whitespace (matters for inline text).
    if translated and source[:1].isspace() and not translated[:1].isspace():
        translated = " " + translated
    if translated and source[-1:].isspace() and not translated[-1:].isspace():
        translated += " "
    return translated


def placeholders(text):
    return sorted(m.group(0) for m in PROTECT_RE.finditer(text))


def _chunks(texts):
    batch, size = [], 0
    for text in texts:
        if batch and (len(batch) >= MAX_ITEMS_PER_REQUEST or size + len(text) > MAX_CHARS_PER_REQUEST):
            yield batch
            batch, size = [], 0
        batch.append(text)
        size += len(text)
    if batch:
        yield batch


def pending(catalog):
    """(message, [source texts]) for every entry with no translation yet."""
    for message in catalog:
        if not message.id or message.fuzzy:
            continue
        if isinstance(message.id, (list, tuple)):
            strings = message.string if isinstance(message.string, (list, tuple)) else (message.string,)
            if not any(strings):
                yield message, [message.id[0], message.id[1]]
        elif not message.string:
            yield message, [message.id]


def fill_catalog(catalog, language, backend):
    """Translate every untranslated entry of ``catalog`` into ``language``.

    Returns (entries translated, characters sent, entries skipped because the
    translation lost a placeholder).
    """
    todo = list(pending(catalog))
    sources = [text for _message, texts in todo for text in texts]
    results = {}
    for batch in _chunks(list(dict.fromkeys(sources))):
        for source, translated in zip(batch, backend.translate([_protect(s) for s in batch], language)):
            results[source] = _finish(source, translated)

    done = skipped = 0
    for message, texts in todo:
        out = [results[text] for text in texts]
        # A translation that dropped or mangled a %(placeholder)s would crash the page.
        if any(placeholders(src) != placeholders(dst) for src, dst in zip(texts, out)):
            skipped += 1
            continue
        if len(texts) == 2:  # plural: singular form first, every other form gets the plural
            forms = max(catalog.num_plurals, 1)
            message.string = tuple([out[0]] + [out[1]] * (forms - 1))
        else:
            message.string = out[0]
        if MACHINE_COMMENT not in message.auto_comments:
            message.auto_comments.append(MACHINE_COMMENT)
        done += 1
    return done, sum(len(s) for s in dict.fromkeys(sources)), skipped
