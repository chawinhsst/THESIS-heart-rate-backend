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

# RunningSessionSerializer remains the same for file uploads
class RunningSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunningSession
        fields = '__all__'
        read_only_fields = ['uploaded_at', 'timeseries_data']

# --- ADD THIS NEW SERIALIZER ---
class SessionLabelUpdateSerializer(serializers.ModelSerializer):
    """A simple serializer for updating only the admin_label."""
    class Meta:
        model = RunningSession
        fields = ['admin_label']