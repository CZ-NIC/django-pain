"""AJAX helper views."""
from django.http import Http404, JsonResponse

from django_pain.processors import get_processor_instance


def load_processor_client_choices(request):
    """Load client choices from the appropriate payment processor."""
    try:
        processor = get_processor_instance(request.GET['processor'])
        return JsonResponse(processor.get_client_choices())
    except (KeyError, ImportError, AttributeError):
        raise Http404
