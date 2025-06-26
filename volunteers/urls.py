from django.urls import path
# UPDATE THIS IMPORT
from .views import VolunteerCreateView, EmailCheckView

urlpatterns = [
    path('', VolunteerCreateView.as_view(), name='volunteer-create'),
    # ADD THIS NEW URL PATTERN
    path('check-email/', EmailCheckView.as_view(), name='check-email'),
]