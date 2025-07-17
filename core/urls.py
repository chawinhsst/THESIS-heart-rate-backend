from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from volunteers import views

router = DefaultRouter()
router.register(r'volunteers', views.VolunteerViewSet, basename='volunteer')
router.register(r'sessions', views.RunningSessionViewSet, basename='session')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/login/', views.CustomLoginView.as_view(), name='api_token_auth'),
    
    # This is the new, dedicated URL for updating labels with JSON data.
    path('api/sessions/<int:pk>/update_label/', views.SessionLabelUpdateView.as_view(), name='session-update-label'),
    
    # This includes all the other routes for volunteers and sessions.
    path('api/', include(router.urls)),
]