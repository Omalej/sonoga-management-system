from django.contrib import admin
from .models import Room, Guest, Reservation, FolioCharge, Payment, HousekeepingTask

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'room_type', 'rate', 'status')
    list_filter = ('status', 'room_type')

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'id_number')
    search_fields = ('name', 'email', 'phone')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'guest', 'guest_name', 'room', 'check_in_date', 'check_out_date', 'status')
    list_filter = ('status', 'check_in_date')

@admin.register(FolioCharge)
class FolioChargeAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'description', 'amount', 'outlet', 'created_at')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'amount', 'payment_method', 'created_at')

@admin.register(HousekeepingTask)
class HousekeepingTaskAdmin(admin.ModelAdmin):
    list_display = ('room', 'task_description', 'status', 'assigned_to', 'created_at')
    list_filter = ('status',)
