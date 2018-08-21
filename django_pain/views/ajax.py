"""AJAX helper views."""
from django.http import Http404, JsonResponse

from django_pain.settings import get_processor_instance


def load_processor_client_choices(request):
    """Load client choices from the appropriate payment processor."""
    try:
        processor = get_processor_instance(request.GET.get('processor', ''))
    except ValueError:
        raise Http404

    if hasattr(processor, 'get_client_choices'):
        return JsonResponse(processor.get_client_choices())
    else:
        raise Http404
