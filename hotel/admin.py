from django.contrib import admin
from .models import (
    RoomType, Room, Guest, Reservation, Stay, Folio, FolioCharge,
    Payment, HousekeepingTask, MaintenanceTicket,
)

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "business_unit", "base_rate", "is_active")
    list_filter = ("business_unit", "is_active")
    search_fields = ("code", "name")

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "room_type", "business_unit", "occupancy_status", "housekeeping_status", "maintenance_status", "is_blocked")
    list_filter = ("business_unit", "room_type", "occupancy_status", "housekeeping_status", "maintenance_status", "is_blocked")
    search_fields = ("number",)

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email", "nationality")
    search_fields = ("first_name", "last_name", "phone", "email", "identification_number")

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("reservation_number", "guest", "source", "arrival_date", "departure_date", "room_type", "assigned_room", "status")
    list_filter = ("business_unit", "source", "status", "room_type")
    search_fields = ("reservation_number", "external_reference", "guest__first_name", "guest__last_name", "guest__phone")

@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = ("guest", "room", "checked_in_at", "checked_out_at", "status")
    list_filter = ("status", "room__business_unit")

@admin.register(Folio)
class FolioAdmin(admin.ModelAdmin):
    list_display = ("stay", "charges_total", "payments_total", "balance", "is_closed")

@admin.register(FolioCharge)
class FolioChargeAdmin(admin.ModelAdmin):
    list_display = ("folio", "charge_type", "description", "amount", "is_void", "created_at")
    list_filter = ("charge_type", "is_void")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "amount", "method", "status", "received_by", "created_at")
    list_filter = ("method", "status")
    search_fields = ("reference", "external_reference")

@admin.register(HousekeepingTask)
class HousekeepingTaskAdmin(admin.ModelAdmin):
    list_display = ("room", "task_type", "assigned_to", "status", "priority", "updated_at")
    list_filter = ("status", "priority", "room__business_unit")

@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "business_unit", "room", "fault_category", "priority", "status", "cost")
    list_filter = ("business_unit", "priority", "status")
    search_fields = ("ticket_number", "fault_category", "description")
