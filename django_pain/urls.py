"""django_pain url dispatcher."""
from django.contrib import admin
from django.urls import include, path

from django_pain.views import load_processor_client_choices

app_name = 'pain'
urlpatterns = [
    path('admin/', admin.site.urls),
    path('ajax/processor_client_choices/', load_processor_client_choices, name='processor_client_choices'),
    path('django_lang_switch/', include('django_lang_switch.urls')),
]
