from django.contrib import admin
from django.urls import path, include # Make sure to import 'include'

urlpatterns = [
    path('admin/', admin.site.urls),
    # Any URL starting with 'api/volunteers/' will be handled by our volunteers app.
    path('api/volunteers/', include('volunteers.urls')),
]