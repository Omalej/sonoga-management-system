from django.urls import path
from . import views
app_name = "reports"
urlpatterns = [
    path("", views.management_dashboard, name="management"),
    path("export.csv", views.management_csv, name="management_csv"),
]
