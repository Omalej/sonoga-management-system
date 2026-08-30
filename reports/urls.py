from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [

    # CEO / Group Management Dashboard
    path(
        "management/",
        views.management_dashboard,
        name="management",
    ),

    # Management CSV Export
    path(
        "management.csv",
        views.management_csv,
        name="management_csv",
    ),

]
