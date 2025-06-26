from django.shortcuts import render
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Volunteer
from .serializers import VolunteerSerializer, EmailCheckSerializer
from django.core.mail import send_mail
from django.conf import settings # Import Django's settings

def index_view(request):
    """
    A simple view to render the informational homepage.
    """
    return render(request, 'volunteers/index.html')
class VolunteerCreateView(generics.CreateAPIView):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer

    # This method is called by Django right after a volunteer is saved.
    def perform_create(self, serializer):
        # First, save the volunteer object to the database as normal.
        volunteer = serializer.save()

        # --- Email Sending Logic ---
        try:
            # --- Email 1: Notification to Admin ---
            admin_subject = f"New Volunteer Registration: {volunteer.first_name} {volunteer.last_name}"
            admin_message = f"""
            A new volunteer has registered for the Heart Rate Anomaly study.

            Name: {volunteer.first_name} {volunteer.last_name}
            Email: {volunteer.email}
            Registration Date: {volunteer.registration_date.strftime('%Y-%m-%d %H:%M')}

            Please log in to the admin panel to view their full details.
            """
            send_mail(
                subject=admin_subject,
                message=admin_message,
                from_email='no-reply@heart-rate-study.com', # A placeholder "from" address
                recipient_list=[settings.ADMIN_EMAIL], # Sends to the admin email from your settings
                fail_silently=False,
            )

            # --- Email 2: Confirmation to Volunteer ---
            volunteer_subject = "Registration Confirmation: Heart Rate Anomaly Study"
            volunteer_message = f"""
            Dear {volunteer.first_name},

            Thank you for registering to participate in the Heart Rate Anomaly Detection research project. Your interest and contribution are greatly appreciated.

            The principal researcher will contact you shortly with the official consent form and instructions on how to submit your data.

            Sincerely,
            Chawin Hansasuta
            """
            send_mail(
                subject=volunteer_subject,
                message=volunteer_message,
                from_email='no-reply@heart-rate-study.com',
                recipient_list=[volunteer.email], # Sends to the email the volunteer provided
                fail_silently=False,
            )

        except Exception as e:
            # If emails fail for any reason, it will print an error in your backend terminal
            # but will not crash the user's registration process.
            print(f"An error occurred while sending emails: {e}")


class EmailCheckView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = EmailCheckSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            is_taken = Volunteer.objects.filter(email__iexact=email).exists()
            return Response({'is_taken': is_taken})
        return Response(serializer.errors, status=400)