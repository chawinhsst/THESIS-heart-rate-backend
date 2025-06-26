from django.contrib import admin
from django.urls import path, include
from volunteers.views import index_view # 1. Import the new view

urlpatterns = [
    # 2. Add this new path for the root URL
    path('', index_view, name='home'),
    
    path('admin/', admin.site.urls),
    path('api/volunteers/', include('volunteers.urls')),
]