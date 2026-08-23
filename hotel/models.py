from django.db import models
from django.conf import settings
from django.utils import timezone

class Room(models.Model):
    ROOM_STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Dirty', 'Dirty'),
        ('Maintenance', 'Maintenance'),
    ]
    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=50)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ROOM_STATUS_CHOICES, default='Available')

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type})"

class Guest(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    id_number = models.CharField(max_length=50, blank=True, null=True)

    @property
    def full_name(self):
        return self.name

    def __str__(self):
        return self.name

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('Confirmed', 'Confirmed'),
        ('Checked-In', 'Checked-In'),
        ('Checked-Out', 'Checked-Out'),
        ('Cancelled', 'Cancelled'),
    ]
    SOURCE_CHOICES = [
        ('Direct', 'Direct / Walk-in'),
        ('WordPress', 'WordPress Website'),
        ('Agent', 'Travel Agent'),
    ]
    reservation_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='Direct')
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    room_type_name = models.CharField(max_length=50, blank=True, null=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Confirmed')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def arrival_date(self):
        return self.check_in_date

    @property
    def departure_date(self):
        return self.check_out_date

    @property
    def room_type(self):
        class DummyType:
            def __init__(self, name):
                self.name = name
        return DummyType(self.room.room_type if self.room else (self.room_type_name or "Standard"))

    def __str__(self):
        name = self.guest.name if self.guest else (self.guest_name or "Guest")
        return f"Reservation {self.reservation_number or self.pk} - {name}"

class FolioCharge(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='charges', default=1)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    outlet = models.CharField(max_length=50, default='Front Desk')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - ?{self.amount}"

class Payment(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='Cash')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment ?{self.amount} for {self.reservation}"

class HousekeepingTask(models.Model):
    TASK_STATUS = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    task_description = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='Pending')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Housekeeping for Room {self.room.room_number} - {self.status}"

class MaintenanceTicket(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Emergency', 'Emergency'),
    ]
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    issue_description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, default='Open')
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Maintenance Room {self.room.room_number} - {self.issue_description[:30]}"
