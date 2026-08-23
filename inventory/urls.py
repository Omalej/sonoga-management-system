from django.urls import path
from . import views

app_name = "inventory"
urlpatterns = [
    path("", views.inventory_dashboard, name="dashboard"),
    path("movements/", views.movement_list, name="movements"),
    path("adjustment/", views.stock_adjustment, name="adjustment"),
    path("transfer/", views.stock_transfer, name="transfer"),
]
