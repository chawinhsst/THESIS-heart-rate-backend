from django.db import models

class Volunteer(models.Model):
    # Personal Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True) # blank=True makes it optional
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True) # unique=True ensures no duplicate emails
    phone = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=20)
    nationality = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    
    # Running Habit Information
    platform = models.CharField(max_length=100)
    smartwatch = models.CharField(max_length=100)
    run_frequency = models.CharField(max_length=100)

    # Consent and Timestamps
    consent_acknowledged = models.BooleanField(default=False)
    registration_date = models.DateTimeField(auto_now_add=True) # Automatically records when the registration happened

    # This special method gives a human-readable name to each volunteer in the admin panel.
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"