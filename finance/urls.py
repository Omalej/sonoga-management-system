from django.urls import path
from . import views

app_name = "finance"
urlpatterns = [
    path("", views.finance_dashboard, name="dashboard"),
    path("expenses/", views.expense_list, name="expenses"),
    path("expenses/new/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/", views.expense_detail, name="expense_detail"),
    path("expenses/<int:pk>/approve/", views.expense_approve, name="expense_approve"),
    path("expenses/<int:pk>/payment/", views.expense_payment, name="expense_payment"),
]
