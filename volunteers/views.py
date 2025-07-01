from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from django_filters.rest_framework import DjangoFilterBackend
from .models import Volunteer
from .serializers import VolunteerSerializer, EmailCheckSerializer


# This view for the informational homepage remains and is unchanged.
def index_view(request):
    """
    A simple view to render the informational homepage.
    """
    return render(request, 'volunteers/index.html')


# This is the new, secure login view that returns an authentication token.
# It is exempt from CSRF because token authentication provides its own security.
@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username
        })


# This view for checking if an email exists remains the same.
class EmailCheckView(APIView):
    permission_classes = [permissions.AllowAny] # Allow anyone to check an email

    def post(self, request, *args, **kwargs):
        serializer = EmailCheckSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            is_taken = Volunteer.objects.filter(email__iexact=email).exists()
            return Response({'is_taken': is_taken})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# The ViewSet for managing volunteers, now with specific permissions per action.
class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all().order_by('-registration_date')
    serializer_class = VolunteerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_permissions(self):
        """
        Sets permissions based on the action.
        - 'create' (public volunteer registration) is allowed for anyone.
        - All other actions (list, update, delete, approve) require an authenticated admin user.
        """
        if self.action == 'create':
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return super(VolunteerViewSet, self).get_permissions()

    def perform_create(self, serializer):
        """
        This method is called when a new volunteer registers.
        It saves the volunteer and sends notification emails.
        """
        volunteer = serializer.save()
        try:
            # --- Email 1: Notification to Admin ---
            admin_subject = f"New Volunteer Registration: {volunteer.first_name} {volunteer.last_name}"
            admin_message = f"A new volunteer has registered for the Heart Rate Anomaly study.\n\nName: {volunteer.first_name} {volunteer.last_name}\nEmail: {volunteer.email}\n\nPlease log in to the admin panel to review and approve them."
            send_mail(
                subject=admin_subject,
                message=admin_message,
                from_email='no-reply@heart-rate-study.com',
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            # --- Email 2: Confirmation to Volunteer ---
            volunteer_subject = "Registration Confirmation: Heart Rate Anomaly Study"
            volunteer_message = f"Dear {volunteer.first_name},\n\nThank you for registering to participate in the Heart Rate Anomaly Detection research project. Your interest and contribution are greatly appreciated.\n\nYour application is now pending review. The principal researcher will contact you shortly.\n\nSincerely,\nChawin Hansasuta"
            send_mail(
                subject=volunteer_subject,
                message=volunteer_message,
                from_email='no-reply@heart-rate-study.com',
                recipient_list=[volunteer.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"An error occurred while sending emails: {e}")

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """
        Custom action to approve a volunteer. Accessible at /api/volunteers/{id}/approve/
        """
        volunteer = self.get_object()
        if volunteer.status == Volunteer.STATUS_PENDING:
            volunteer.status = Volunteer.STATUS_APPROVED
            volunteer.save()
            return Response({'status': 'volunteer approved'})
        return Response({'status': 'volunteer was not in pending state'}, status=status.HTTP_400_BAD_REQUEST)