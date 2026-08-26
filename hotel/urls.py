from django.urls import path
from . import views

app_name = "hotel"

urlpatterns = [
    # Dashboard
    path(
        "",
        views.hotel_dashboard,
        name="dashboard",
    ),

    # Reservations
    path(
        "reservations/",
        views.reservation_list,
        name="reservations",
    ),

    path(
        "reservations/new/",
        views.reservation_create,
        name="reservation_create",
    ),

    path(
        "reservations/<int:pk>/",
        views.reservation_detail,
        name="reservation_detail",
    ),

    path(
        "reservations/<int:pk>/check-in/",
        views.reservation_checkin,
        name="reservation_checkin",
    ),

    path(
        "reservations/<int:pk>/swap-guest/",
        views.reservation_swap_guest,
        name="reservation_swap_guest",
    ),

    # Guests
    path(
        "guests/new/",
        views.guest_create,
        name="guest_create",
    ),

    # Stays
    path(
        "stays/<int:pk>/",
        views.stay_detail,
        name="stay_detail",
    ),

    path(
        "stays/<int:pk>/check-out/",
        views.stay_checkout,
        name="stay_checkout",
    ),

    # Folio
    path(
        "folios/<int:pk>/payment/",
        views.folio_payment,
        name="folio_payment",
    ),

    # Housekeeping
    path(
        "housekeeping/",
        views.housekeeping_list,
        name="housekeeping",
    ),

    path(
        "housekeeping/<int:pk>/",
        views.housekeeping_update,
        name="housekeeping_update",
    ),

    path(
        "housekeeping/<int:pk>/verify/",
        views.housekeeping_verify,
        name="housekeeping_verify",
    ),

    # WordPress
    path(
        "webhooks/wordpress/",
        views.wordpress_booking_webhook,
        name="wordpress_booking_webhook",
    ),
]