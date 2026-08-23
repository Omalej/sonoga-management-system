from django.urls import path
from . import views

app_name = 'hotel'

urlpatterns = [
    path('', views.hotel_dashboard, name='dashboard'),
    path('reservations/', views.reservation_list, name='reservation_list'),
    path('reservations/new/', views.manual_reservation, name='manual_reservation'),
    path('sync-wordpress/', views.sync_wordpress_bookings, name='sync_wordpress'),
    path('api/wp-webhook/', views.wordpress_booking_webhook, name='wp_webhook'),
]
