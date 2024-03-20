from django.conf import settings


def shared_api_keys(request):
    """
    Pass some variables from the settings to the template context
    :param request:
    :return:
    """
    return {
        'WHAT3WORDS_API_KEY': settings.WHAT3WORDS_API_KEY,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        }
