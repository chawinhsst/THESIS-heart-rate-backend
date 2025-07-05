from django.shortcuts import render
from django.core.mail import send_mail, EmailMultiAlternatives # 1. Import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string # 2. Import render_to_string
from django.utils.html import strip_tags # 3. Import strip_tags

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
def backend_homepage_view(request):
    """
    A simple view to render the informational homepage for the backend root.
    """
    return render(request, 'volunteers/index.html')


# This is the secure login view that returns a token.
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


# The ViewSet for managing volunteers.
class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all().order_by('-registration_date')
    serializer_class = VolunteerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return super(VolunteerViewSet, self).get_permissions()

    def perform_create(self, serializer):
        """
        This method is called when a new volunteer registers.
        It saves the volunteer and sends both a plain-text admin notification
        and a beautiful HTML confirmation email to the volunteer.
        """
        volunteer = serializer.save()
        try:
            # --- Email 1: Plain-text Notification to Admin ---
            admin_subject = f"New Volunteer Registration: {volunteer.first_name} {volunteer.last_name}"
            admin_message = f"A new volunteer has registered for the Heart Rate Anomaly study.\n\nName: {volunteer.first_name} {volunteer.last_name}\nEmail: {volunteer.email}\n\nPlease log in to the admin panel to review and approve them."
            send_mail(
                subject=admin_subject,
                message=admin_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            # --- Email 2: Beautiful HTML Confirmation to Volunteer ---
            volunteer_subject = "Registration Confirmation: Heart Rate Anomaly Study"
            
            # Data to pass into the new HTML template
            context = {
                'first_name': volunteer.first_name,
                'last_name': volunteer.last_name,
                'email': volunteer.email,
                'date_of_birth': volunteer.date_of_birth,
                'gender': volunteer.gender,
                'nationality': volunteer.nationality,
                'platform': volunteer.platform,
                'smartwatch': volunteer.smartwatch,
                'run_frequency': volunteer.run_frequency,
            }
            # Render the HTML content from the template file
            html_content = render_to_string('volunteers/volunteer_confirmation_email.html', context)
            # Create a plain text version automatically for email clients that don't support HTML
            text_content = strip_tags(html_content)

            # Create the email message
            email = EmailMultiAlternatives(
                subject=volunteer_subject,
                body=text_content, # The plain text version
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[volunteer.email] # Send to the volunteer's email address
            )
            # Attach the HTML version
            email.attach_alternative(html_content, "text/html")
            email.send()

        except Exception as e:
            print(f"An error occurred while sending emails: {e}")

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        volunteer = self.get_object()
        if volunteer.status == Volunteer.STATUS_PENDING:
            volunteer.status = Volunteer.STATUS_APPROVED
            volunteer.save()
            # You could add logic here to send another email notifying the user of their approval
            return Response({'status': 'volunteer approved'})
        return Response({'status': 'volunteer was not in pending state'}, status=status.HTTP_400_BAD_REQUEST)