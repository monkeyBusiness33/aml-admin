

class OpsPortalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.app_mode = 'ops_portal'

        response = self.get_response(request)
        return response
