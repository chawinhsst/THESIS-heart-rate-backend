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
    # --- Status field for background task tracking ---
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]
    
    # --- Core Relationship & Uploaded File ---
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='sessions')
    session_date = models.DateTimeField()
    source_type = models.CharField(max_length=50, help_text="e.g., 'admin_upload'")
    session_file = models.FileField(upload_to='session_files/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PROCESSING)
    
    # --- ADD THIS FIELD ---
    processing_error = models.TextField(blank=True, null=True, help_text="Stores the error message if processing fails")

    # --- Fields for Summarized Data (populated by background task) ---
    total_distance_km = models.FloatField(null=True, blank=True, help_text="Total distance in kilometers")
    total_duration_secs = models.FloatField(null=True, blank=True, help_text="Total duration in seconds")
    avg_heart_rate = models.IntegerField(null=True, blank=True, help_text="Average heart rate in bpm")
    max_heart_rate = models.IntegerField(null=True, blank=True, help_text="Maximum heart rate in bpm")
    
    # --- Field for full time-series data ---
    timeseries_data = models.JSONField(blank=True, null=True, help_text="Stores the full time-series data from the file")

    # --- Fields for ML analysis ---
    ml_prediction = models.CharField(max_length=100, blank=True, null=True)
    ml_confidence = models.FloatField(blank=True, null=True)
    admin_label = models.CharField(max_length=100, blank=True, null=True)

    # --- Metadata ---
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session for {self.volunteer.email} on {self.session_date.strftime('%Y-%m-%d')}"