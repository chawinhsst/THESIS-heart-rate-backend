# backend/volunteers/views.py

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
from django.db import transaction

from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
# --- 1. IMPORT JSONParser ---
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.filters import OrderingFilter

from django_filters.rest_framework import DjangoFilterBackend
from .models import Volunteer, RunningSession
from .serializers import (
    VolunteerSerializer,
    EmailCheckSerializer,
    RunningSessionSerializer,
    SessionLabelUpdateSerializer,
    RecordLabelUpdateSerializer
)
from .tasks import process_session_file
from .pagination import CustomPageNumberPagination


def backend_homepage_view(request):
    return render(request, 'volunteers/index.html')


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


class EmailCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = EmailCheckSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            is_taken = Volunteer.objects.filter(email__iexact=email).exists()
            return Response({'is_taken': is_taken})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SessionLabelUpdateView(generics.UpdateAPIView):
    queryset = RunningSession.objects.all()
    serializer_class = SessionLabelUpdateSerializer
    permission_classes = [permissions.IsAdminUser]


class RunningSessionViewSet(viewsets.ModelViewSet):
    serializer_class = RunningSessionSerializer
    permission_classes = [permissions.IsAdminUser]
    # --- 2. ADD JSONParser TO THE LIST OF PARSERS ---
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = [
        'session_date',
        'total_distance_km',
        'total_duration_secs',
        'avg_heart_rate',
        'max_heart_rate',
    ]

    def get_queryset(self):
        queryset = RunningSession.objects.all().select_related('volunteer')
        volunteer_id = self.request.query_params.get('volunteer')
        if volunteer_id is not None:
            queryset = queryset.filter(volunteer_id=volunteer_id)
        
        if self.action == 'list':
            queryset = queryset.defer('timeseries_data')
            
        return queryset
        
    @action(detail=True, methods=['patch'], url_path='update-anomalies')
    def update_anomalies(self, request, pk=None):
        session = self.get_object()
        updates = request.data.get('updates', [])

        if not isinstance(updates, list) or not session.timeseries_data:
            return Response(
                {"error": "Invalid data format or no timeseries data in session."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            with transaction.atomic():
                update_map = {item['timestamp']: item['anomaly'] for item in updates}
                for record in session.timeseries_data:
                    if record.get('timestamp') in update_map:
                        record['anomaly'] = update_map[record['timestamp']]
                session.save(update_fields=['timeseries_data'])
            
            return Response({"status": "success", "message": f"{len(updates)} records checked."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['patch'], url_path='label-records', serializer_class=RecordLabelUpdateSerializer)
    def label_records(self, request, pk=None):
        session = self.get_object()
        serializer = self.get_serializer(instance=session, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'anomaly labels updated successfully'})

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        session_file = request.data.get('session_file')
        if session_file:
            instance.session_file = session_file
            instance.status = RunningSession.STATUS_PROCESSING
            instance.processing_error = None
            instance.timeseries_data = None
            instance.total_distance_km = None
            instance.total_duration_secs = None
            instance.avg_heart_rate = None
            instance.max_heart_rate = None
            instance.save()
            process_session_file.delay(instance.id)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        session_instance = serializer.save()
        if session_instance.session_file:
            process_session_file.delay(session_instance.id)


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