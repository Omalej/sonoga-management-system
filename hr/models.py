from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from organization.models import BusinessUnit, Department, Position

class Employee(TimeStampedModel):
    class EmploymentType(models.TextChoices):
        PERMANENT = 'Permanent', 'Permanent'
        CONTRACT = 'Contract', 'Contract'
        CASUAL = 'Casual', 'Casual'
        TEMPORARY = 'Temporary', 'Temporary'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        ON_LEAVE = 'On Leave', 'On Leave'
        SUSPENDED = 'Suspended', 'Suspended'
        RESIGNED = 'Resigned', 'Resigned'
        TERMINATED = 'Terminated', 'Terminated'
        RETIRED = 'Retired', 'Retired'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile')
    staff_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50)
    
    # Personal & Location Details
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    state_of_origin = models.CharField(max_length=50, blank=True)
    lga = models.CharField(max_length=50, blank=True, verbose_name="Local Government Area")
    passport = models.ImageField(upload_to='employee_passports/', null=True, blank=True)

    # Organizational Structure
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name='employees')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')

    # Employment Details
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.PERMANENT)
    employment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Financial & Banking
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    bank_name = models.CharField(max_length=100, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)

    
    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name} {self.last_name}".replace('  ', ' ').strip()


    def save(self, *args, **kwargs):
        if not self.staff_number:
            last_emp = Employee.objects.all().order_by('-id').first()
            next_id = (last_emp.id + 1) if last_emp else 1
            self.staff_number = f"SFG-{next_id:04d}"

        # Auto-generate a user account if not already linked
        if not self.user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            base_username = f"{self.first_name.lower()}.{self.last_name.lower()}".replace(" ", "")
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create a default user account with a secure temporary password
            new_user = User.objects.create_user(
                username=username,
                email=self.email or f"{username}@sonogagroup.com",
                first_name=self.first_name,
                last_name=self.last_name,
                password="SonogaPassword2026!"
            )
            self.user = new_user

        super().save(*args, **kwargs)
        if not self.staff_number:
            last_emp = Employee.objects.all().order_by('-id').first()
            next_id = (last_emp.id + 1) if last_emp else 1
            self.staff_number = f"SFG-{next_id:04d}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.staff_number} - {self.first_name} {self.last_name}"

class LeaveRequest(TimeStampedModel):
    class LeaveType(models.TextChoices):
        ANNUAL = 'Annual', 'Annual Leave'
        SICK = 'Sick', 'Sick Leave'
        CASUAL = 'Casual', 'Casual Leave'
        MATERNITY = 'Maternity', 'Maternity Leave'
        UNPAID = 'Unpaid', 'Unpaid Leave'

    class LeaveStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending Approval'
        APPROVED = 'Approved', 'Approved'
        REJECTED = 'Rejected', 'Rejected'
        CANCELED = 'Canceled', 'Canceled'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.ANNUAL)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.start_date} to {self.end_date})"
