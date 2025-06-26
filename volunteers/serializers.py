from rest_framework import serializers
from .models import Volunteer

# This serializer is for creating a new volunteer (already exists)
class VolunteerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = '__all__'

# ADD THIS NEW CLASS
class EmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)