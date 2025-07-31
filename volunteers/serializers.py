# backend/volunteers/serializers.py

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
    """
    This serializer is updated to ensure the large timeseries_data field
    is handled correctly and not editable directly.
    """
    volunteer_first_name = serializers.CharField(source='volunteer.first_name', read_only=True)
    volunteer_last_name = serializers.CharField(source='volunteer.last_name', read_only=True)
    
    # This explicitly defines the timeseries_data field as a read-only JSON field.
    # It's a good practice for clarity and safety.
    timeseries_data = serializers.JSONField(read_only=True)
    
    class Meta:
        model = RunningSession
        # The 'fields' list is updated to be explicit, which is better than '__all__'
        fields = [
            'id', 'volunteer', 'session_date', 'source_type', 'session_file', 
            'status', 'processing_error', 'total_distance_km', 'total_duration_secs',
            'avg_heart_rate', 'max_heart_rate', 'timeseries_data', 'ml_prediction',
            'ml_confidence', 'admin_label', 'uploaded_at', 'volunteer_first_name',
            'volunteer_last_name',
        ]
        # The read_only_fields are also updated for clarity.
        read_only_fields = [
            'status', 'processing_error', 'total_distance_km', 'total_duration_secs',
            'avg_heart_rate', 'max_heart_rate', 'uploaded_at', 'volunteer_first_name', 
            'volunteer_last_name'
        ]

# SessionLabelUpdateSerializer remains the same
class SessionLabelUpdateSerializer(serializers.ModelSerializer):
    """A simple serializer for updating only the session-level admin_label."""
    class Meta:
        model = RunningSession
        fields = ['admin_label']


# --- NEW SERIALIZER ---
# This is the new class required for the labeling feature. It is self-contained
# and does not affect any other part of your code.
class RecordLabelUpdateSerializer(serializers.Serializer):
    """
    Serializer to validate the list of anomalous timestamps for a session.
    This also contains the logic to update the session's JSON data.
    """
    anomalous_timestamps = serializers.ListField(
        child=serializers.CharField(),
        help_text="A list of timestamp strings for records to be marked as anomalous."
    )

    def update(self, instance, validated_data):
        """
        This method is called when .save() is executed on the serializer in the view.
        It updates the 'Anomaly' flag within the JSONField.
        """
        anomalous_ts_set = set(validated_data.get('anomalous_timestamps', []))
        
        if instance.timeseries_data is None:
            # Cannot label records if there are none, so we do nothing.
            return instance

        # Iterate through the records and update the 'Anomaly' flag
        for record in instance.timeseries_data:
            if record.get('timestamp') in anomalous_ts_set:
                record['Anomaly'] = 1
            else:
                # This part is crucial to un-mark records that are no longer considered anomalous
                record['Anomaly'] = 0
        
        instance.save()
        return instance