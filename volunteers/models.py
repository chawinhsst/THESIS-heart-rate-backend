from django.db import models

class Volunteer(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
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


class RunningSession(models.Model):
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='sessions')
    session_date = models.DateTimeField()
    source_type = models.CharField(max_length=50, help_text="e.g., 'admin_upload'")
    
    # This field will handle the file upload itself
    session_file = models.FileField(upload_to='session_files/', blank=True, null=True)

    # This field will store the parsed CSV data as JSON
    timeseries_data = models.JSONField(blank=True, null=True)

    # Fields for your ML analysis
    ml_prediction = models.CharField(max_length=100, blank=True, null=True)
    ml_confidence = models.FloatField(blank=True, null=True)
    admin_label = models.CharField(max_length=100, blank=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session for {self.volunteer.email} on {self.session_date.strftime('%Y-%m-%d')}"