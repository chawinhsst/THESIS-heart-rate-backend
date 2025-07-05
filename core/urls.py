from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from volunteers import views

router = DefaultRouter()
router.register(r'volunteers', views.VolunteerViewSet, basename='volunteer')

urlpatterns = [
    # This new path points the root URL to our informational homepage view
    path('', views.backend_homepage_view, name='home'),
    
    path('admin/', admin.site.urls),
    path('api-auth/login/', views.CustomLoginView.as_view(), name='api_token_auth'),
    path('api/', include(router.urls)),
]