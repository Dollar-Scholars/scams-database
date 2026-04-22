from django.shortcuts import render, redirect
from django.db.models import Avg, Sum
from .forms import ScamReportForm
from .models import Scam
from django.db.models.functions import ExtractYear
from django.db.models.functions import ExtractMonth
from django.db.models.functions import TruncMonth
from django.db.models import Count
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

def scam_list(request):
    scams = Scam.objects.all().order_by('-created_at')
    return render(request, 'scams/scam_list.html', {'scams': scams})


def dashboard(request):
    year = request.GET.get('year')
    month = request.GET.get('month')
    year_o = request.GET.get('year_o')
    month_o = request.GET.get('month_o')

    scams = Scam.objects.all()

    if year:
        scams = scams.filter(created_at__year=year)

    if month:
        scams = scams.filter(created_at__month=month)

    scams = scams.order_by('-created_at')

    scams_o = Scam.objects.all()

    if year_o:
        scams_o = scams_o.filter(date_occurred__year=year_o)

    if month_o:
        scams_o = scams_o.filter(date_occurred__month=month_o)

    scams_o = scams_o.order_by('-date_occurred')

    # dynamic years for filter
    years = (
        Scam.objects
        .annotate(year=ExtractYear('created_at'))
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year')
    )
    
    years_o = (
        Scam.objects
        .annotate(year_o=ExtractYear('date_occurred'))
        .values_list('year_o', flat=True)
        .distinct()
        .order_by('-year_o')
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

    month_qs_o = Scam.objects.all()

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
    MONTH_NAMES = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    months = [(m, MONTH_NAMES[m]) for m in months_raw]
    months_o = [(m, MONTH_NAMES[m]) for m in months_raw_o]

    chart_data_o = (
    scams_o
    .annotate(month=TruncMonth('date_occurred'))
    .values('month')
    .annotate(count=Count('id'))
    .order_by('month')
    )
    
    labels_o = []
    data_o = []

    for entry in chart_data_o:
        labels_o.append(entry['month'].strftime("%b %Y"))  
        data_o.append(entry['count'])
    


    chart_data= (
    scams
    .annotate(month=TruncMonth('created_at'))
    .values('month')
    .annotate(count=Count('id'))
    .order_by('month')
    )
    
    labels = []
    data = []

    for entry in chart_data:
        labels.append(entry['month'].strftime("%b %Y"))  # e.g. "Jan 2026"
        data.append(entry['count'])

    loss= (scams.aggregate(total=Sum('amount_lost'))['total'] or 0)
    scam_reported= (scams_o.aggregate(total=Count('id'))['total'] or 0)
    loss_o= (scams_o.aggregate(total=Sum('amount_lost'))['total'] or 0)

    return render(request, "scams/dashboard.html", {
        "scams": scams,
        "years": years,
        "months": months,
        "selected_year": year,
        "selected_month": month,
        "scams_o": scams_o,
        "years_o": years_o,
        "months_o": months_o,
        "selected_year_o": year_o,
        "selected_month_o": month_o,
        "chart_labels": json.dumps(labels),
        "chart_data": json.dumps(data),
        "chart_labels_o": json.dumps(labels_o),
        "chart_data_o": json.dumps(data_o),
        "total_loss": loss,
        "total_loss_o": loss_o,
        "total_scams_o": scam_reported,


    })

