from django.urls import path
from . import views

app_name = "hr"
urlpatterns = [
    path("", views.hr_dashboard, name="dashboard"),
    path("employees/", views.employee_list, name="employees"),
    path("employees/new/", views.employee_create, name="employee_create"),
]
