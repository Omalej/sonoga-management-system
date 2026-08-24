from django.urls import path
from . import views

app_name = 'hotel'

urlpatterns = [
    path('', views.hotel_dashboard, name='dashboard'),
    path('reservations/', views.reservation_list, name='reservation_list'),
    path('reservations/new/', views.reservation_create, name='reservation_create'),
    path('reservations/<int:pk>/', views.reservation_detail, name='reservation_detail'),
    path('reservations/<int:pk>/checkin/', views.reservation_checkin, name='reservation_checkin'),
    path('stays/<int:pk>/', views.stay_detail, name='stay_detail'),
    path('stays/<int:pk>/payment/', views.folio_payment, name='folio_payment'),
    path('stays/<int:pk>/checkout/', views.stay_checkout, name='stay_checkout'),
    path('housekeeping/', views.housekeeping_list, name='housekeeping'),
    path('housekeeping/<int:pk>/update/', views.housekeeping_update, name='housekeeping_update'),
    path('housekeeping/<int:pk>/verify/', views.housekeeping_verify, name='housekeeping_verify'),
    path('api/wp-webhook/', views.wordpress_booking_webhook, name='wp_webhook'),
]
