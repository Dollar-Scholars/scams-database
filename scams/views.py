from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.db.models import Sum
from .contributors import CONTRIBUTORS
from .forms import ScamReportForm
from .models import Scam, CURRENCY_CHOICES
from django.db.models.functions import ExtractYear
from django.db.models.functions import ExtractMonth
from django.db.models.functions import TruncMonth
from django.db.models import Count, F
from urllib.parse import urlencode
import json

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
    resources = [
        {
            'name': 'Federal Trade Commission (FTC)',
            'url': 'https://reportfraud.ftc.gov/',
            'description': 'File a report with the Federal Trade Commission.',
        },
        {
            'name': 'FBI Internet Crime Complaint Center (IC3)',
            'url': 'https://www.ic3.gov/',
            'description': 'Report internet-based fraud.',
        },
        {
            'name': 'Consumer Financial Protection Bureau (CFPB)',
            'url': 'https://www.consumerfinance.gov/',
            'description': 'Learn your rights and file a complaint about a financial company.',
        },
        {
            'name': 'USA.gov',
            'url': 'https://www.usa.gov/legal-aid',
            'description': 'For legal help and services.',
        },
    ]
    return render(request, 'scams/scam_awareness_page.html', {
        'resources': resources,
        # The thank-you page links here with ?from=report; everyone else arrives from the
        # site nav, so the "thank you for your report" wording is only shown to reporters.
        'from_report': request.GET.get('from') == 'report',
    })

REPORTS_PER_PAGE = 25

# Columns the public "All reports" page shows. Loading only these keeps the reporter's
# name, email and phone (and the long description) out of the page entirely.
SCAM_LIST_FIELDS = ('title', 'scam_type', 'contact_method', 'date_occurred', 'country', 'status', 'created_at')


def scam_list(request):
    scams = Scam.objects.only(*SCAM_LIST_FIELDS).order_by('-created_at', '-pk')
    paginator = Paginator(scams, REPORTS_PER_PAGE)
    # get_page() never raises: a non-number gives page 1, an out-of-range number the last page.
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'scams/scam_list.html', {
        'scams': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'page_range': paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
    })


# --- Dashboard helpers ---------------------------------------------------------------

MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

# "USD — US Dollar" -> "US Dollar"; "Other" stays "Other".
CURRENCY_NAMES = {code: label[len(code):].lstrip(' —–-') or label for code, label in CURRENCY_CHOICES}

# Months with no reports are drawn as 0 so the chart's time axis is even, unless the
# range is longer than this (e.g. one report of a scam from decades ago).
DASHBOARD_MAX_FILLED_MONTHS = 240

# The "Latest reports" table: how many rows, and the only columns it loads. The
# reporter's name, email and phone are never loaded for this public page.
DASHBOARD_RECENT_COUNT = 10
DASHBOARD_RECENT_FIELDS = ('title', 'scam_type', 'date_occurred', 'amount_lost', 'currency', 'status', 'created_at')


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
        return f'{MONTH_NAMES[month]} {year}'
    if year:
        return str(year)
    if month:
        return f'{MONTH_NAMES[month]}, any year'
    return 'All time'


def _monthly_counts(queryset, field, only_month=None):
    """[(label, count)] per calendar month of `field`, oldest first. Rows where the
    field is NULL are left out, and empty months inside the range count as 0.
    With `only_month` (a month filter without a year) only that month of each year
    is filled in, so the filtered-out months never show up as months with 0 reports."""
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
    return [(f'{MONTH_NAMES[m]} {y}', counts.get((y, m), 0)) for y, m in months]


def _chart_summary(series, description):
    """One sentence describing a monthly series, used as the canvas's accessible name."""
    if not series:
        return ''
    first, last = series[0][0], series[-1][0]
    peak_label, peak = max(series, key=lambda row: row[1])
    span = first if first == last else f'{first} to {last}'
    noun = 'report' if peak == 1 else 'reports'
    return (f'{description}, {span}. Busiest month: {peak_label} with {peak} {noun}. '
            f'Exact numbers are in the table below the chart.')


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
            'label': CURRENCY_NAMES.get(row['currency'], row['currency']) if row['currency'] else 'Currency not given',
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

    # convert to (number, name)
    months = [(m, MONTH_NAMES[m]) for m in _with_selected(months_raw, month) if m in MONTH_NAMES]
    months_o = [(m, MONTH_NAMES[m]) for m in _with_selected(months_raw_o, month_o) if m in MONTH_NAMES]

    series = _monthly_counts(scams, 'created_at', only_month=month)
    series_o = _monthly_counts(scams_o, 'date_occurred', only_month=month_o)
    labels = [label for label, _ in series]  # e.g. "Jan 2026"
    data = [count for _, count in series]
    labels_o = [label for label, _ in series_o]
    data_o = [count for _, count in series_o]

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
        "recent_scams": list(scams.only(*DASHBOARD_RECENT_FIELDS)[:DASHBOARD_RECENT_COUNT]),
        "chart_rows": series,
        "chart_rows_o": series_o,
        "chart_summary": _chart_summary(series, 'Bar chart of reports submitted per month'),
        "chart_summary_o": _chart_summary(series_o, 'Bar chart of scams by the month they occurred'),
        # Rendered with json_script, so no user text can break out of the <script>.
        "chart_json": {
            "submitted": {"labels": labels, "data": data},
            "occurred": {"labels": labels_o, "data": data_o},
        },
        # Each card's reset link clears only its own filter and keeps the other card's.
        "reset_query": query(year_o=year_o, month_o=month_o),
        "reset_query_o": query(year=year, month=month),
    })

