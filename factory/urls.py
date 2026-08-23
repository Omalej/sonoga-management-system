from django.urls import path
from . import views

app_name = "factory"
urlpatterns = [
    path("", views.factory_dashboard, name="dashboard_default"),
    path("<str:code>/", views.factory_dashboard, name="dashboard"),
    path("<str:code>/batches/", views.batch_list, name="batches"),
    path("<str:code>/batches/new/", views.batch_create, name="batch_create"),
    path("<str:code>/batches/<int:pk>/", views.batch_detail, name="batch_detail"),
    path("<str:code>/batches/<int:pk>/materials/new/", views.batch_add_material, name="batch_add_material"),
    path("<str:code>/batches/<int:pk>/approve/", views.batch_approve, name="batch_approve"),
    path("<str:code>/sales/", views.sales_list, name="sales"),
    path("<str:code>/sales/new/", views.sales_create, name="sales_create"),
    path("<str:code>/sales/<int:pk>/", views.sales_detail, name="sales_detail"),
    path("<str:code>/sales/<int:pk>/lines/new/", views.sales_add_line, name="sales_add_line"),
    path("<str:code>/sales/<int:pk>/confirm/", views.sales_confirm, name="sales_confirm"),
    path("<str:code>/sales/<int:pk>/payment/", views.sales_payment, name="sales_payment"),
]
