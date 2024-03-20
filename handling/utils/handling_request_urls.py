import urllib.parse

from django.urls import reverse
from django.conf import settings

from firebase_dynamic_links import DynamicLinks

from core.utils.helpers import get_ops_portal_url


def get_firebase_dynamic_link(handling_request):
    handling_request_uri = reverse('admin:handling_request', kwargs={'pk': handling_request.pk})

    # Get URL prepending part
    ops_portal_url = get_ops_portal_url()
    if settings.DEBUG:
        ops_portal_url = 'https://dev.amlglobal.net/'

    # Generate full URL to S&F Request Details Page
    handling_request_url = urllib.parse.urljoin(ops_portal_url, handling_request_uri)

    api_key = settings.FIREBASE_API_KEY
    domain = 'amlglobal.page.link'
    timeout = 10
    dl = DynamicLinks(api_key, domain, timeout)
    params = {
        "androidInfo": {
            "androidPackageName": 'aero.aml_global',
            "androidFallbackLink": handling_request_url,
            "androidMinPackageVersionCode": '1'
        },
        "iosInfo": {
            "iosBundleId": "aero.amlGlobal",
            "iosFallbackLink": handling_request_url,
            "iosAppStoreId": "1585624707"
        },
        "socialMetaTagInfo": {
            "socialTitle": '{callsign} / {airport} / {arrival_datetime}Z'.format(
                callsign=handling_request.callsign,
                airport=handling_request.location_tiny_repr,
                arrival_datetime=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M"),
            ),
            "socialImageLink": urllib.parse.urljoin(ops_portal_url,
                                                    '/static/assets/img/handling/sf_request_status_new.png'),
        }
    }
    shortened_link = dl.generate_dynamic_link(handling_request_url, False, params)

    return shortened_link
