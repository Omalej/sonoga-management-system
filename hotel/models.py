from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from core.models import TimeStampedModel
from organization.models import BusinessUnit


class RoomType(TimeStampedModel):
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="room_types")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    standard_capacity = models.PositiveSmallIntegerField(default=1)
    maximum_capacity = models.PositiveSmallIntegerField(default=2)
    base_rate = models.DecimalField(max_digits=14, decimal_places=2)
    extra_person_charge = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amenities = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["business_unit", "code"], name="uniq_roomtype_code_per_unit"),
            models.UniqueConstraint(fields=["business_unit", "name"], name="uniq_roomtype_name_per_unit"),
        ]

    def clean(self):
        if self.business_unit_id and self.business_unit.unit_type != BusinessUnit.UnitType.HOTEL:
            raise ValidationError({"business_unit": "Room types must belong to a hotel business unit."})

    def __str__(self):
        return self.name


class Room(TimeStampedModel):
    class Occupancy(models.TextChoices):
        VACANT = "VACANT", "Vacant"
        OCCUPIED = "OCCUPIED", "Occupied"

    class Housekeeping(models.TextChoices):
        CLEAN = "CLEAN", "Clean"
        DIRTY = "DIRTY", "Dirty"
        CLEANING = "CLEANING", "Cleaning"
        INSPECTION = "INSPECTION", "Inspection"

    class Maintenance(models.TextChoices):
        CLEAR = "CLEAR", "Clear"
        REPORTED = "REPORTED", "Reported"
        UNDER_REPAIR = "UNDER_REPAIR", "Under Repair"
        OUT_OF_SERVICE = "OUT_OF_SERVICE", "Out of Service"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="rooms")
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    number = models.CharField(max_length=20)
    floor = models.CharField(max_length=50, blank=True)
    occupancy_status = models.CharField(max_length=20, choices=Occupancy.choices, default=Occupancy.VACANT)
    housekeeping_status = models.CharField(max_length=20, choices=Housekeeping.choices, default=Housekeeping.CLEAN)
    maintenance_status = models.CharField(max_length=20, choices=Maintenance.choices, default=Maintenance.CLEAR)
    is_blocked = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["business_unit", "number"], name="uniq_room_number_per_unit")]

    def clean(self):
        errors = {}
        if self.room_type_id and self.business_unit_id and self.room_type.business_unit_id != self.business_unit_id:
            errors["room_type"] = "Room type must belong to the same business unit."
        if self.business_unit_id and self.business_unit.unit_type != BusinessUnit.UnitType.HOTEL:
            errors["business_unit"] = "Rooms must belong to a hotel business unit."
        if errors:
            raise ValidationError(errors)

    @property
    def is_ready(self):
        return (
            self.occupancy_status == self.Occupancy.VACANT
            and self.housekeeping_status == self.Housekeeping.CLEAN
            and self.maintenance_status == self.Maintenance.CLEAR
            and not self.is_blocked
        )

    def __str__(self):
        return f"Room {self.number}"


class Guest(TimeStampedModel):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=30, db_index=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    identification_type = models.CharField(max_length=80, blank=True)
    identification_number = models.CharField(max_length=120, blank=True)
    preferences = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name


class Reservation(TimeStampedModel):
    class Source(models.TextChoices):
        WORDPRESS = "WORDPRESS", "WordPress Website"
        WALK_IN = "WALK_IN", "Walk-in"
        PHONE = "PHONE", "Phone"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        CORPORATE = "CORPORATE", "Corporate"
        AGENT = "AGENT", "Agent"
        MANUAL = "MANUAL", "Manual"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No-show"
        CHECKED_IN = "CHECKED_IN", "Checked-in"
        CHECKED_OUT = "CHECKED_OUT", "Checked-out"

    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="reservations")
    reservation_number = models.CharField(max_length=40, unique=True)
    external_reference = models.CharField(max_length=120, blank=True, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="reservations")
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="reservations")
    assigned_room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True, related_name="reservations")
    arrival_date = models.DateField()
    departure_date = models.DateField()
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)
    nightly_rate = models.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    special_requests = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_reservations")

    class Meta:
        ordering = ["-arrival_date", "reservation_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_reference"],
                condition=~models.Q(external_reference=""),
                name="uniq_external_booking_ref_per_source",
            )
        ]

    def clean(self):
        errors = {}
        if self.departure_date and self.arrival_date and self.departure_date <= self.arrival_date:
            errors["departure_date"] = "Departure date must be after arrival date."
        if self.room_type_id and self.business_unit_id and self.room_type.business_unit_id != self.business_unit_id:
            errors["room_type"] = "Room type must belong to the selected hotel."
        if self.assigned_room_id:
            if self.assigned_room.business_unit_id != self.business_unit_id:
                errors["assigned_room"] = "Assigned room must belong to the selected hotel."
            elif self.assigned_room.room_type_id != self.room_type_id:
                errors["assigned_room"] = "Assigned room must match the reserved room type."
        if errors:
            raise ValidationError(errors)

    @property
    def nights(self):
        return max((self.departure_date - self.arrival_date).days, 0)

    @property
    def accommodation_total(self):
        return (self.nightly_rate * self.nights) - self.discount_amount + self.tax_amount

    def __str__(self):
        return f"{self.reservation_number} - {self.guest}"


class Stay(TimeStampedModel):
    class Status(models.TextChoices):
        IN_HOUSE = "IN_HOUSE", "In House"
        CHECKED_OUT = "CHECKED_OUT", "Checked-out"

    reservation = models.OneToOneField(Reservation, on_delete=models.PROTECT, related_name="stay")
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="stays")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="stays")
    checked_in_at = models.DateTimeField()
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="checkins")
    checked_out_at = models.DateTimeField(null=True, blank=True)
    checked_out_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="checkouts")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_HOUSE)

    def clean(self):
        if self.room_id and not self.pk and not self.room.is_ready:
            raise ValidationError({"room": "Room must be vacant, clean, clear of maintenance, and unblocked before check-in."})

    def __str__(self):
        return f"{self.guest} - {self.room}"


class Folio(TimeStampedModel):
    stay = models.OneToOneField(Stay, on_delete=models.PROTECT, related_name="folio")
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)

    @property
    def charges_total(self):
        return self.charges.filter(is_void=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def payments_total(self):
        return self.payments.filter(status=Payment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def balance(self):
        return self.charges_total - self.payments_total

    def __str__(self):
        return f"Folio - {self.stay}"


class FolioCharge(TimeStampedModel):
    class ChargeType(models.TextChoices):
        ROOM = "ROOM", "Room"
        RESTAURANT = "RESTAURANT", "Restaurant"
        BAR = "BAR", "Bar"
        LAUNDRY = "LAUNDRY", "Laundry"
        DAMAGE = "DAMAGE", "Damage"
        OTHER = "OTHER", "Other"

    folio = models.ForeignKey(Folio, on_delete=models.PROTECT, related_name="charges")
    charge_type = models.CharField(max_length=20, choices=ChargeType.choices)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="folio_charges")
    is_void = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.charge_type} - {self.amount}"


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        POS = "POS", "POS"
        TRANSFER = "TRANSFER", "Bank Transfer"
        ONLINE = "ONLINE", "Online"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        REVERSED = "REVERSED", "Reversed"

    folio = models.ForeignKey(Folio, on_delete=models.PROTECT, null=True, blank=True, related_name="payments")
    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT, null=True, blank=True, related_name="payments")
    reference = models.CharField(max_length=80, unique=True)
    external_reference = models.CharField(max_length=120, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hotel_payments_received")
    notes = models.TextField(blank=True)

    def clean(self):
        if bool(self.folio_id) == bool(self.reservation_id):
            raise ValidationError("A payment must belong to exactly one folio or reservation.")

    def __str__(self):
        return f"{self.reference} - {self.amount}"


class HousekeepingTask(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        CLEANING = "CLEANING", "Cleaning"
        COMPLETED = "COMPLETED", "Completed"
        VERIFIED = "VERIFIED", "Verified"

    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="housekeeping_tasks")
    task_type = models.CharField(max_length=80, default="Checkout Cleaning")
    assigned_to = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="housekeeping_tasks")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=20, default="Normal")
    notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_housekeeping_tasks")

    def __str__(self):
        return f"{self.room} - {self.status}"


class MaintenanceTicket(TimeStampedModel):
    class Status(models.TextChoices):
        REPORTED = "REPORTED", "Reported"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        VERIFIED = "VERIFIED", "Verified"
        CANCELLED = "CANCELLED", "Cancelled"

    ticket_number = models.CharField(max_length=40, unique=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="maintenance_tickets")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True, related_name="maintenance_tickets")
    location = models.CharField(max_length=150, blank=True)
    fault_category = models.CharField(max_length=100)
    description = models.TextField()
    priority = models.CharField(max_length=20, default="Normal")
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_maintenance_tickets")
    assigned_to = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_assignments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REPORTED)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.ticket_number} - {self.fault_category}"
