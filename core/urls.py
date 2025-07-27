from django.contrib import admin
from django.urls import path, include
from volunteers.views import backend_homepage_view # <-- Import the view

# Import the CustomLoginView from your volunteers app
from volunteers.views import CustomLoginView

urlpatterns = [
    # Add this line for the root URL
    path('', backend_homepage_view, name='backend_homepage'),
    path('admin/', admin.site.urls),
    
    # This is the new line that fixes the 404 error.
    # It creates the /api-auth/login/ endpoint your frontend is looking for.
    path('api-auth/login/', CustomLoginView.as_view(), name='api_login'),
    
    # This line correctly includes all other URLs (sessions, volunteers, etc.)
    # from your volunteers app under the /api/ prefix.
    path('api/', include('volunteers.urls')),
]