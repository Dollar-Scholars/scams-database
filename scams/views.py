from django.shortcuts import render, redirect
from .forms import ScamReportForm
from .models import Scam


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