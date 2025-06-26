from django.contrib import admin
from .models import Volunteer

# This line makes the Volunteer model visible on the admin site.
admin.site.register(Volunteer)