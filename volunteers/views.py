from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Volunteer
from .serializers import VolunteerSerializer


@ensure_csrf_cookie
def get_csrf_token(request):
    """
    This view sets the CSRF cookie on the client.
    """
    return JsonResponse({"detail": "CSRF cookie set"})

# This view for the informational homepage remains the same.
def index_view(request):
    """
    A simple view to render the informational homepage.
    """
    return render(request, 'volunteers/index.html')


# This new ViewSet replaces the old VolunteerCreateView and EmailCheckView
class VolunteerViewSet(viewsets.ModelViewSet):
    """
    This ViewSet automatically provides `list` (GET), `create` (POST), `retrieve` (GET /id),
    `update` (PUT/PATCH /id), and `destroy` (DELETE /id) actions for the Volunteer model.
    """
    queryset = Volunteer.objects.all().order_by('-registration_date')
    serializer_class = VolunteerSerializer
    permission_classes = [permissions.IsAdminUser] # Ensures only admin users can access
    
    # This enables filtering by the 'status' field in the URL
    # e.g., /api/volunteers/?status=pending
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def perform_create(self, serializer):
        """
        This method is called when a new volunteer is created via a POST request.
        We keep our email notification logic here.
        """
        volunteer = serializer.save()

        try:
            # --- Email 1: Notification to Admin ---
            admin_subject = f"New Volunteer Registration: {volunteer.first_name} {volunteer.last_name}"
            admin_message = f"""
            A new volunteer has registered for the Heart Rate Anomaly study.

            Name: {volunteer.first_name} {volunteer.last_name}
            Email: {volunteer.email}
            Registration Date: {volunteer.registration_date.strftime('%Y-%m-%d %H:%M')}

            Please log in to the admin panel to review and approve them.
            """
            send_mail(
                subject=admin_subject,
                message=admin_message,
                from_email='no-reply@heart-rate-study.com',
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            # --- Email 2: Confirmation to Volunteer ---
            volunteer_subject = "Registration Confirmation: Heart Rate Anomaly Study"
            volunteer_message = f"""
            Dear {volunteer.first_name},

            Thank you for registering to participate in the Heart Rate Anomaly Detection research project. Your interest and contribution are greatly appreciated.

            Your application is now pending review. The principal researcher will contact you shortly.

            Sincerely,
            Chawin Hansasuta
            """
            send_mail(
                subject=volunteer_subject,
                message=volunteer_message,
                from_email='no-reply@heart-rate-study.com',
                recipient_list=[volunteer.email],
                fail_silently=False,
            )

        except Exception as e:
            print(f"An error occurred while sending emails: {e}")

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Custom action to approve a volunteer. Accessible at /api/volunteers/{id}/approve/
        """
        volunteer = self.get_object()
        if volunteer.status == Volunteer.STATUS_PENDING:
            volunteer.status = Volunteer.STATUS_APPROVED
            volunteer.save()
            # Optionally, you could send another email here notifying them of approval
            return Response({'status': 'volunteer approved'})
        return Response({'status': 'volunteer was not in pending state'}, status=400)
    
    