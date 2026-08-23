from django.urls import path
from . import views
app_name = "procurement"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/submit/", views.request_submit, name="request_submit"),
    path("requests/<int:pk>/approve/", views.request_approve, name="request_approve"),
    path("orders/new/", views.order_create, name="order_create"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/issue/", views.order_issue, name="order_issue"),
    path("receipts/new/", views.receipt_create, name="receipt_create"),
    path("receipts/<int:pk>/", views.receipt_detail, name="receipt_detail"),
    path("receipts/<int:pk>/post/", views.receipt_post, name="receipt_post"),
]
