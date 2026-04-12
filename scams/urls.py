from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_scam, name='report_scam'),
    path('thank-you/', views.thank_you, name='thank_you'),
    path('all-scams/', views.scam_list, name='scam_list'),
]