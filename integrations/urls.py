from django.urls import path
from .views import wordpress_booking_webhook, wordpress_ping

app_name = "integrations"
urlpatterns = [
    path("wordpress/ping/", wordpress_ping, name="wordpress_ping"),
    path("wordpress/bookings/", wordpress_booking_webhook, name="wordpress_booking_webhook"),
]
