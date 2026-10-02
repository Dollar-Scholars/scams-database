"""ScamDB's English wording, for dollarscholars.org to translate.

ScamDB's translations are made and reviewed on dollarscholars.org, with its own wording
(docs/TRANSLATIONS.md). It reads the list this module writes, translation_sources.json at
the top of the repository, straight from GitHub's main branch, so the file is committed
and a test fails when it is out of date (python manage.py export_translation_sources).

Same rules as dollarscholars.org's translations/extract.py: templates are compiled with
Django's own template engine, so the text is exactly what Django looks up when the page
renders. Plurals ({% plural %}, ngettext) are not supported there; use wording that needs
none, such as "Reports: %(count)s".
"""
import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.template import engines
from django.template.base import Origin, Template, TemplateSyntaxError
from django.templatetags.i18n import BlockTranslateNode, TranslateNode

FORMAT_VERSION = 1
SOURCES_FILE = Path(settings.BASE_DIR) / 'translation_sources.json'

GETTEXT_FUNCTIONS = {'_', 'gettext', 'gettext_lazy', 'gettext_noop'}
PGETTEXT_FUNCTIONS = {'pgettext', 'pgettext_lazy'}
PLURAL_FUNCTIONS = {'ngettext', 'ngettext_lazy', 'npgettext', 'npgettext_lazy'}
PLACEHOLDER_RE = re.compile(r'%\((\w+)\)[sdif]')
# Two placeholders with only a word or two between them, as in "%(a)s of %(b)s": machine
# translation tends to drop those words ("2 of 4" came back as "2 4" in 22 languages).
WORDS_BETWEEN_RE = re.compile(r'%\(\w+\)[sdif]\s+[^\W\d_]+(?:\s+[^\W\d_]+)?\s+%\(\w+\)[sdif]')


@dataclass
class Message:
    text: str
    context: str = ''
    is_format: bool = False
    locations: set = field(default_factory=set)


class Extraction:
    def __init__(self):
        self.messages = {}
        self.warnings = []   # wording that can't be collected: must be fixed
        self.skipped = []    # templates Django can't compile (so no page can use them)

    def add(self, text, context, is_format, location):
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        if not text.strip():
            return
        if WORDS_BETWEEN_RE.search(text):
            self.warnings.append(
                f'{location}: {text!r}: a word or two between two placeholders gets lost in '
                'machine translation; keep the numbers out of the text (e.g. "2/4")')
        message = self.messages.get((context, text))
        if message is None:
            message = self.messages[(context, text)] = Message(text, context, is_format)
        message.is_format = message.is_format or is_format
        message.locations.add(location)

    def as_json(self):
        messages = sorted(self.messages.values(),
                          key=lambda m: (_first_location(m), m.context, m.text))
        data = {
            'version': FORMAT_VERSION,
            'messages': [{'text': m.text, 'context': m.context, 'is_format': m.is_format,
                          'locations': sorted(m.locations, key=_location_key)}
                         for m in messages],
        }
        return json.dumps(data, ensure_ascii=False, indent=1) + '\n'


def _location_key(location):
    path, _, line = location.rpartition(':')
    return (path, int(line) if line.isdigit() else 0)


def _first_location(message):
    return min((_location_key(place) for place in message.locations), default=('', 0))


def _literal(filter_expression):
    """The string of a literal template argument like "Hello", else None."""
    if filter_expression is None or filter_expression.filters:
        return None
    var = filter_expression.var
    if isinstance(var, str):  # quoted constants are stored already resolved
        return str(var)
    literal = getattr(var, 'literal', None)
    return literal if isinstance(literal, str) else None


def _relative(path):
    return Path(path).resolve().relative_to(Path(settings.BASE_DIR).resolve()).as_posix()


def extract_template(path, extraction):
    name = _relative(path)
    source = Path(path).read_text(encoding='utf-8')
    try:
        template = Template(source, origin=Origin(str(path), name),
                            engine=engines['django'].engine)
    except TemplateSyntaxError as exc:
        extraction.skipped.append(f'{name}: template error, skipped: {exc}')
        return
    for node in template.nodelist.get_nodes_by_type(TranslateNode):
        location = f'{name}:{node.token.lineno}'
        text = _literal(node.filter_expression)
        if text is None:
            extraction.warnings.append(f'{location}: translate of a variable is not collected')
            continue
        context = _context(node, location, extraction)
        if context is not None:
            extraction.add(text, context, False, location)
    for node in template.nodelist.get_nodes_by_type(BlockTranslateNode):
        location = f'{name}:{node.token.lineno}'
        if node.plural:
            extraction.warnings.append(
                f'{location}: {{% plural %}} is not supported; reword without a plural')
        text, _vars = node.render_token_list(node.singular)
        context = _context(node, location, extraction)
        if context is not None:
            extraction.add(text, context, True, location)


def _context(node, location, extraction):
    if node.message_context is None:
        return ''
    context = _literal(node.message_context)
    if context is None:
        extraction.warnings.append(f'{location}: non-literal context, not collected')
    return context


def _string_arg(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_python(path, extraction):
    name = _relative(path)
    try:
        tree = ast.parse(Path(path).read_text(encoding='utf-8'), filename=name)
    except SyntaxError as exc:
        extraction.warnings.append(f'{name}: syntax error, skipped: {exc}')
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.id if isinstance(func, ast.Name) else getattr(func, 'attr', None)
        location = f'{name}:{node.lineno}'
        if func_name in GETTEXT_FUNCTIONS and node.args:
            text = _string_arg(node.args[0])
            if text is not None:
                extraction.add(text, '', bool(PLACEHOLDER_RE.search(text)), location)
        elif func_name in PGETTEXT_FUNCTIONS and len(node.args) >= 2:
            context, text = _string_arg(node.args[0]), _string_arg(node.args[1])
            if context is not None and text is not None:
                extraction.add(text, context, bool(PLACEHOLDER_RE.search(text)), location)
        elif func_name in PLURAL_FUNCTIONS:
            extraction.warnings.append(
                f'{location}: {func_name}() is not supported; reword without a plural')


def local_app_dirs():
    base = Path(settings.BASE_DIR).resolve()
    dirs = []
    for config in apps.get_app_configs():
        path = Path(config.path).resolve()
        if path.is_relative_to(base) and not {'.venv', 'venv'} & set(path.parts):
            dirs.append(path)
    return dirs


def template_dirs():
    base = Path(settings.BASE_DIR).resolve()
    dirs = [Path(d) for d in engines['django'].engine.dirs]
    dirs += [d / 'templates' for d in local_app_dirs() if (d / 'templates').is_dir()]
    return [d for d in dirs if d.resolve().is_relative_to(base)]


def extract_all():
    extraction = Extraction()
    for directory in template_dirs():
        for path in sorted(Path(directory).rglob('*.html')):
            if 'admin' in path.relative_to(directory).parts:
                continue  # the admin stays in English
            extract_template(path, extraction)
    for directory in local_app_dirs():
        for path in sorted(Path(directory).rglob('*.py')):
            parts = path.relative_to(directory).parts
            if 'migrations' in parts or 'tests' in parts or path.name.startswith('test'):
                continue
            extract_python(path, extraction)
    return extraction
