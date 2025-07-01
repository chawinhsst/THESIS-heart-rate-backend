from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from volunteers import views
from volunteers.views import get_csrf_token # 1. Import the new view

router = DefaultRouter()
router.register(r'volunteers', views.VolunteerViewSet, basename='volunteer')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),

    # 2. Add this new URL for our handshake
    path('api/get-csrf-token/', get_csrf_token, name='get-csrf-token'),
]