from django.urls import path
from . import views
app_name = "payroll"
urlpatterns = [
    path("", views.payroll_list, name="list"),
    path("new/", views.payroll_create, name="create"),
    path("<int:pk>/", views.payroll_detail, name="detail"),
    path("<int:pk>/generate/", views.payroll_generate, name="generate"),
    path("<int:pk>/lines/<int:line_id>/edit/", views.payroll_line_edit, name="line_edit"),
    path("<int:pk>/approve/", views.payroll_approve, name="approve"),
    path("<int:pk>/paid/", views.payroll_paid, name="paid"),
]
