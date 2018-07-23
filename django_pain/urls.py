"""django_pain url dispatcher."""
from django.contrib import admin
from django.urls import path

app_name = 'pain'
urlpatterns = [
    path('admin/', admin.site.urls),
]
