"""django_pain test url dispatcher."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django_pain.urls', namespace='pain')),
]
