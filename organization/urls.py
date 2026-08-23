from django.urls import path
from .views import company_department_list

app_name = "organization"
urlpatterns = [
    path("companies/", company_department_list, name="company_list"),
]
