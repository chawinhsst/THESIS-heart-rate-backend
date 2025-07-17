import io
import pandas as pd
import numpy as np
from django.shortcuts import render
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser

from django_filters.rest_framework import DjangoFilterBackend
from .models import Volunteer, RunningSession
from .serializers import VolunteerSerializer, EmailCheckSerializer, RunningSessionSerializer


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
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = EmailCheckSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            is_taken = Volunteer.objects.filter(email__iexact=email).exists()
            return Response({'is_taken': is_taken})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# A dedicated view for updating only the admin label.
class SessionLabelUpdateView(generics.UpdateAPIView):
    queryset = RunningSession.objects.all()
    serializer_class = RunningSessionSerializer
    permission_classes = [permissions.IsAdminUser]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data={'admin_label': request.data.get('admin_label')}, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


# This ViewSet handles file uploads, listing, and deleting sessions.
class RunningSessionViewSet(viewsets.ModelViewSet):
    serializer_class = RunningSessionSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser] # Expects file data

    def get_queryset(self):
        queryset = RunningSession.objects.all().order_by('-session_date')
        volunteer_id = self.request.query_params.get('volunteer')
        if volunteer_id is not None:
            queryset = queryset.filter(volunteer_id=volunteer_id)
        return queryset

    def perform_create(self, serializer):
        volunteer = Volunteer.objects.get(id=self.request.data.get('volunteer'))
        session_file = self.request.data.get('session_file')
        
        timeseries_data_list = None
        if session_file:
            try:
                df = pd.read_csv(io.StringIO(session_file.read().decode('utf-8')))
                df = df.replace({np.nan: None})
                timeseries_data_list = df.to_dict(orient='records')
            except Exception as e:
                print(f"Error parsing CSV file: {e}")
        
        serializer.save(
            volunteer=volunteer,
            source_type='admin_upload',
            timeseries_data=timeseries_data_list
        )


# Your existing VolunteerViewSet for managing volunteer details and status.
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
        volunteer = serializer.save()
        try:
            admin_subject = f"New Volunteer Registration: {volunteer.first_name} {volunteer.last_name}"
            admin_message = f"A new volunteer has registered for the Heart Rate Anomaly study.\n\nName: {volunteer.first_name} {volunteer.last_name}\nEmail: {volunteer.email}\n\nPlease log in to the admin panel to review and approve them."
            send_mail(
                subject=admin_subject,
                message=admin_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            volunteer_subject = "Registration Confirmation: Heart Rate Anomaly Study"
            context = { 'first_name': volunteer.first_name, 'last_name': volunteer.last_name, 'email': volunteer.email, 'date_of_birth': volunteer.date_of_birth, 'gender': volunteer.gender, 'nationality': volunteer.nationality, 'platform': volunteer.platform, 'smartwatch': volunteer.smartwatch, 'run_frequency': volunteer.run_frequency, }
            html_content = render_to_string('volunteers/volunteer_confirmation_email.html', context)
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                subject=volunteer_subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[volunteer.email]
            )
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
            return Response({'status': 'volunteer approved'})
        return Response({'status': 'volunteer was not in pending state'}, status=status.HTTP_400_BAD_REQUEST)