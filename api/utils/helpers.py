
def get_mobile_app_version(request):
    """
    Function to parse API request header HTTP_USER_AGENT to fetch mobile app version
    :param request:
    :return:
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '1.0.0')

    if user_agent in ['Dart/2.16 (dart:io)', 'Dart/2.15 (dart:io)', 'Dart/2.14 (dart:io)', ]:
        return '1.1.18'

    if user_agent.startswith('PostmanRuntime'):
        return '9999999'

    version = user_agent.split('AMLAPP/')[-1:]

    return version[0]
