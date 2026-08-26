from django.urls import path
from . import views

app_name = "integrations"

urlpatterns = [
    path("wordpress/booking/", views.wp_booking_webhook, name="wp_booking_webhook"),
]
