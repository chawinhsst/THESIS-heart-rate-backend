from rest_framework import serializers
from .models import Volunteer, RunningSession

# VolunteerSerializer remains the same
class VolunteerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = '__all__'
        read_only_fields = ['registration_date']

# EmailCheckSerializer remains the same
class EmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

# --- UPDATED RunningSessionSerializer ---
class RunningSessionSerializer(serializers.ModelSerializer):
    # This adds the volunteer's full name to the API response for better readability
    # REMOVED: volunteer_name = serializers.CharField(source='volunteer.__str__', read_only=True)

    # --- ADD THESE TWO LINES ---
    # This tells the serializer to look at the related 'volunteer' object
    # and get its 'first_name' and 'last_name' fields.
    volunteer_first_name = serializers.CharField(source='volunteer.first_name', read_only=True)
    volunteer_last_name = serializers.CharField(source='volunteer.last_name', read_only=True)
    
    class Meta:
        model = RunningSession
        fields = '__all__'
        read_only_fields = [
            'status',
            'total_distance_km',
            'total_duration_secs',
            'avg_heart_rate',
            'max_heart_rate',
            'timeseries_data',
            'uploaded_at',
            'volunteer_first_name', # Add new fields here too
            'volunteer_last_name',
        ]

# SessionLabelUpdateSerializer remains the same
class SessionLabelUpdateSerializer(serializers.ModelSerializer):
    """A simple serializer for updating only the admin_label."""
    class Meta:
        model = RunningSession
        fields = ['admin_label']