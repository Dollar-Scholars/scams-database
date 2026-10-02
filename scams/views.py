from django.shortcuts import render, redirect
from django.db.models import Sum
from django.utils.translation import get_language, gettext as _
from .contributors import CONTRIBUTORS
from .forms import ScamReportForm
from .models import Scam, CURRENCY_CHOICES
from django.db.models.functions import ExtractYear
from django.db.models.functions import ExtractMonth
from django.db.models.functions import TruncMonth
from django.db.models import Count, F
from urllib.parse import urlencode
from datetime import date
from functools import lru_cache
import json

from babel import Locale, UnknownLocaleError
from babel.dates import format_date, format_skeleton
from babel.numbers import get_currency_name

def report_scam(request):
    if request.method == "POST":
        form = ScamReportForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('thank_you')  # This points to a URL name
    else:
        form = ScamReportForm()

    return render(request, 'scams/report_form.html', {'form': form})


def thank_you(request):
    return render(request, 'scams/thank_you.html')

def contributors(request):
    return render(request, 'scams/contributors.html', {'contributors': CONTRIBUTORS})


def scam_awareness_page(request):
    # The agencies' names are proper names and stay as they are; what each one is for
    # is translated.
    resources = [
        {
            'name': 'Federal Trade Commission (FTC)',
            'url': 'https://reportfraud.ftc.gov/',
            'description': _('File a report with the Federal Trade Commission.'),
        },
        {
            'name': 'FBI Internet Crime Complaint Center (IC3)',
            'url': 'https://www.ic3.gov/',
            'description': _('Report internet-based fraud.'),
        },
        {
            'name': 'Consumer Financial Protection Bureau (CFPB)',
            'url': 'https://www.consumerfinance.gov/',
            'description': _('Learn your rights and file a complaint about a financial company.'),
        },
        {
            'name': 'USA.gov',
            'url': 'https://www.usa.gov/legal-aid',
            'description': _('For legal help and services.'),
        },
    ]
    return render(request, 'scams/scam_awareness_page.html', {
        'resources': resources,
        # The thank-you page links here with ?from=report; everyone else arrives from the
        # site nav, so the "thank you for your report" wording is only shown to reporters.
        'from_report': request.GET.get('from') == 'report',
    })

# --- Dashboard helpers ---------------------------------------------------------------

# "USD — US Dollar" -> "US Dollar"; "Other" stays "Other". The English fallback for a
# currency Babel has no name for.
CURRENCY_NAMES = {code: label[len(code):].lstrip(' —–-') or label for code, label in CURRENCY_CHOICES}

# Months with no reports are drawn as 0 so the chart's time axis is even, unless the
# range is longer than this (e.g. one report of a scam from decades ago).
DASHBOARD_MAX_FILLED_MONTHS = 240


@lru_cache(maxsize=None)
def _babel_locale(language_code):
    """Babel locale for a Django language code (zh-hans -> zh_Hans, es-mx -> es_MX,
    other '-' -> '_'), falling back to the base language and then to English."""
    parts = (language_code or 'en').replace('_', '-').split('-')
    candidates = []
    if len(parts) > 1:
        region = parts[1].title() if len(parts[1]) == 4 else parts[1].upper()
        candidates.append(f'{parts[0].lower()}_{region}')
    candidates += [parts[0].lower(), 'en']
    for candidate in candidates:
        try:
            return Locale.parse(candidate)
        except (UnknownLocaleError, ValueError):
            continue
    return Locale('en')


def _locale():
    """Babel locale of the language the page is being shown in."""
    return _babel_locale(get_language() or 'en')


def _month_name(month):
    """Short month name on its own, in the page language: "Mar", "mar", "3月"."""
    return format_date(date(2000, month, 1), 'LLL', locale=_locale())


def _month_year(year, month, full=False):
    """Month and year in the page language's own order and words:
    "Mar 2026" / "mar 2026" / "2026年3月", or with full=True "March 2026" / "marzo de 2026"."""
    return format_skeleton('yMMMM' if full else 'yMMM', date(year, month, 1), locale=_locale())


def _currency_name(code):
    """The currency's name in the page language: "US Dollar", "dólar estadounidense"."""
    if code == 'Other':
        return _('Other currency')
    name = get_currency_name(code, locale=_locale())
    if not name or name == code:  # Babel returns the code when it has no name for it
        name = CURRENCY_NAMES.get(code, code)
    return name


def _int_param(request, name, low, high):
    """GET parameter as an int in [low, high], or None when it is missing or invalid."""
    value = request.GET.get(name, '').strip()
    if not (value.isascii() and value.isdigit()):
        return None
    number = int(value)
    return number if low <= number <= high else None


def _with_selected(values, selected, reverse=False):
    """Sorted filter options, without NULLs, always including the selected value so
    the <select> shows the filter that is actually applied."""
    options = {value for value in values if value is not None}
    if selected is not None:
        options.add(selected)
    return sorted(options, reverse=reverse)


def _period_label(year, month):
    if year and month:
        return _month_year(year, month, full=True)  # "March 2026"
    if year:
        return str(year)
    if month:
        # Translators: a month filter with no year chosen, e.g. "March, any year".
        return _('%(month)s, any year') % {
            'month': format_date(date(2000, month, 1), 'LLLL', locale=_locale()),
        }
    return _('All time')


def _monthly_counts(queryset, field, only_month=None):
    """[(label, count)] per calendar month of `field`, oldest first. Rows where the
    field is NULL are left out, and empty months inside the range count as 0.
    With `only_month` (a month filter without a year) only that month of each year
    is filled in, so the filtered-out months never show up as months with 0 reports.
    Labels are in the page language ("Mar 2026", "mar 2026")."""
    rows = (
        queryset
        .filter(**{f'{field}__isnull': False})
        .annotate(month=TruncMonth(field))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    counts = {}
    for row in rows:
        if row['month'] is not None:
            key = (row['month'].year, row['month'].month)
            counts[key] = counts.get(key, 0) + row['count']
    if not counts:
        return []

    months = sorted(counts)
    (first_year, first_month), (last_year, last_month) = months[0], months[-1]
    # The same limit with or without a month filter: the range is measured in months.
    span = (last_year - first_year) * 12 + (last_month - first_month) + 1
    if span <= DASHBOARD_MAX_FILLED_MONTHS:
        if only_month:
            months = [(year, only_month) for year in range(first_year, last_year + 1)]
        else:
            months = [
                (first_year + (first_month - 1 + i) // 12, (first_month - 1 + i) % 12 + 1)
                for i in range(span)
            ]
    return [(_month_year(y, m), counts.get((y, m), 0)) for y, m in months]


def _chart_summary(series, description):
    """One sentence describing a monthly series, used as the canvas's accessible name."""
    if not series:
        return ''
    first, last = series[0][0], series[-1][0]
    peak_label, peak = max(series, key=lambda row: row[1])
    # A range of months, "Jan 2026 – Mar 2026". Not translated: machine translation tends to
    # drop a word between two placeholders ("%(first)s to %(last)s" came back without "to").
    span = first if first == last else f'{first} – {last}'
    return _(
        '%(description)s, %(span)s. Busiest month: %(month)s (reports: %(count)s). '
        'Exact numbers are in the table below the chart.'
    ) % {'description': description, 'span': span, 'month': peak_label, 'count': peak}


def _chart_series(series, label):
    """One chart's data for dashboard.js. All of its text arrives here already in the page
    language: the month labels, the dataset label and one tooltip per bar, in which the
    browser replaces "{count}" with the number formatted for the page language."""
    return {
        'label': label,
        'labels': [month for month, _count in series],
        'data': [count for _month, count in series],
        'tooltips': [
            # Translators: chart tooltip. Keep %(count)s; it becomes the number of reports.
            _('Reports: %(count)s') % {'count': '{count}'}
            for _row in series
        ],
    }


def _losses_by_currency(queryset):
    """Money lost per currency. Amounts in different currencies are never added together,
    and reports with no amount (or an amount of 0) are not counted."""
    rows = (
        queryset
        .filter(amount_lost__gt=0)
        .values('currency')
        .annotate(total=Sum('amount_lost'), count=Count('id'))
        .order_by()
    )
    losses = [
        {
            'code': row['currency'],
            # The ISO code shown on the tile; empty for "Other" and for no currency,
            # which show their (translated) label instead.
            'abbr': row['currency'] if len(row['currency'] or '') == 3 and row['currency'].isupper() else '',
            'label': _currency_name(row['currency']) if row['currency'] else _('Currency not given'),
            'total': row['total'],
            'count': row['count'],
        }
        for row in rows
    ]
    # Most-reported currency first; reports without a currency last.
    losses.sort(key=lambda row: (row['code'] == '', -row['count'], row['code']))
    return losses


def dashboard(request):
    # Invalid or out-of-range values (?year=abc, ?month=13) are ignored instead of raising a 500.
    year = _int_param(request, 'year', 1, 9999)
    month = _int_param(request, 'month', 1, 12)
    year_o = _int_param(request, 'year_o', 1, 9999)
    month_o = _int_param(request, 'month_o', 1, 12)

    scams = Scam.objects.all()

    if year:
        scams = scams.filter(created_at__year=year)

    if month:
        scams = scams.filter(created_at__month=month)

    scams = scams.order_by('-created_at', '-pk')

    scams_o = Scam.objects.all()

    if year_o:
        scams_o = scams_o.filter(date_occurred__year=year_o)

    if month_o:
        scams_o = scams_o.filter(date_occurred__month=month_o)

    # Newest first and reports without a date last, on every database
    # (PostgreSQL would otherwise put NULLs first in a descending sort).
    scams_o = scams_o.order_by(F('date_occurred').desc(nulls_last=True), '-created_at', '-pk')

    # dynamic years for filter
    years = _with_selected(
        Scam.objects
        .annotate(year=ExtractYear('created_at'))
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year'),
        year, reverse=True,
    )

    years_o = _with_selected(
        Scam.objects
        .filter(date_occurred__isnull=False)
        .annotate(year_o=ExtractYear('date_occurred'))
        .values_list('year_o', flat=True)
        .distinct()
        .order_by('-year_o'),
        year_o, reverse=True,
    )

    # dynamic months for filter (based on selected year)
    month_qs = Scam.objects.all()

    if year:
        month_qs = month_qs.filter(created_at__year=year)

    months_raw = (
        month_qs
        .annotate(month=ExtractMonth('created_at'))
        .values_list('month', flat=True)
        .distinct()
        .order_by('month')
    )

    month_qs_o = Scam.objects.filter(date_occurred__isnull=False)

    if year_o:
        month_qs_o = month_qs_o.filter(date_occurred__year=year_o)

    months_raw_o = (
        month_qs_o
        .annotate(month_o=ExtractMonth('date_occurred'))
        .values_list('month_o', flat=True)
        .distinct()
        .order_by('month_o')
    )

    # convert to (number, name), the name in the page language
    months = [(m, _month_name(m)) for m in _with_selected(months_raw, month) if 1 <= m <= 12]
    months_o = [(m, _month_name(m)) for m in _with_selected(months_raw_o, month_o) if 1 <= m <= 12]

    series = _monthly_counts(scams, 'created_at', only_month=month)
    series_o = _monthly_counts(scams_o, 'date_occurred', only_month=month_o)
    labels = [label for label, _count in series]  # e.g. "Jan 2026", in the page language
    data = [count for _label, count in series]
    labels_o = [label for label, _count in series_o]
    data_o = [count for _label, count in series_o]

    # Legacy totals: these add amounts across currencies, so the page shows
    # loss_by_currency / loss_by_currency_o instead.
    loss = (scams.aggregate(total=Sum('amount_lost'))['total'] or 0)
    loss_o = (scams_o.aggregate(total=Sum('amount_lost'))['total'] or 0)

    total_scams = scams.count()
    scam_reported = scams_o.count()
    undated_count_o = 0 if (year_o or month_o) else scams_o.filter(date_occurred__isnull=True).count()

    def query(**params):
        return urlencode({name: value for name, value in params.items() if value})

    return render(request, "scams/dashboard.html", {
        "scams": scams,
        "years": years,
        "months": months,
        "selected_year": str(year) if year else None,
        "selected_month": str(month) if month else None,
        "scams_o": scams_o,
        "years_o": years_o,
        "months_o": months_o,
        "selected_year_o": str(year_o) if year_o else None,
        "selected_month_o": str(month_o) if month_o else None,
        "chart_labels": json.dumps(labels),
        "chart_data": json.dumps(data),
        "chart_labels_o": json.dumps(labels_o),
        "chart_data_o": json.dumps(data_o),
        "total_loss": loss,
        "total_loss_o": loss_o,
        "total_scams_o": scam_reported,
        # Added for the Dollar Scholars layout.
        "has_reports": Scam.objects.exists(),
        "total_scams": total_scams,
        "undated_count_o": undated_count_o,
        "period_label": _period_label(year, month),
        "period_label_o": _period_label(year_o, month_o),
        "loss_by_currency": _losses_by_currency(scams),
        "loss_by_currency_o": _losses_by_currency(scams_o),
        "chart_rows": series,
        "chart_rows_o": series_o,
        "chart_summary": _chart_summary(series, _('Bar chart of reports submitted per month')),
        "chart_summary_o": _chart_summary(series_o, _('Bar chart of scams by the month they occurred')),
        # Rendered with json_script, so no user text can break out of the <script>.
        # It also carries dashboard.js's text, already in the page language.
        "chart_json": {
            "submitted": _chart_series(series, _('Reports submitted')),
            "occurred": _chart_series(series_o, _('Scams that occurred')),
        },
        # Each card's reset link clears only its own filter and keeps the other card's.
        "reset_query": query(year_o=year_o, month_o=month_o),
        "reset_query_o": query(year=year, month=month),
    })
