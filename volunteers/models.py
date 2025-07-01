from django.db import models

class Volunteer(models.Model):
    # --- NEW STATUS FIELD ---
    # We define the choices for the status field as constants for clarity.
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    # This is the new field that will be added to your database table.
    # All new volunteers will automatically be assigned a 'pending' status.
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    # --- All existing fields remain the same ---
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=20)
    nationality = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    
    platform = models.CharField(max_length=100)
    smartwatch = models.CharField(max_length=100)
    run_frequency = models.CharField(max_length=100)

    consent_acknowledged = models.BooleanField(default=False)
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"