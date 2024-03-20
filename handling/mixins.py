from django.http import Http404

from handling.models import HandlingRequest


class GetHandlingRequestMixinOps:
    """
    Mixing helps to pull HandlingRequest instance from the database by 'handling_request_id' or 'pk' url kwarg
    """
    handling_request = None

    def __init__(self):
        self.kwargs = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        handling_request_id = self.kwargs.get('handling_request_id')
        if not handling_request_id:
            handling_request_id = self.kwargs['pk']

        try:
            self.handling_request = HandlingRequest.objects.get(pk=handling_request_id)
        except HandlingRequest.DoesNotExist:
            raise Http404
