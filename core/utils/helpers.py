from django.conf import settings
from django.urls import reverse_lazy


def get_ops_portal_url():
    return f'https://{settings.AML_OPERATIONS_PORTAL_DOMAIN}'


def get_raw_deep_link(url):
    """
    Generate "Deep Link" for AML mobile app
    :param url: string
    :return: string
    """
    return f'https://amlglobal.page.link/?link={url}&apn=aero.aml_global&isi=1585624707&ibi=aero.amlGlobal'


def normalize_phone_number(phone_number: str):
    """
    Function remove certain symbols from the string to normalize phone number
    :param phone_number: string with phone number
    :return:
    """
    result = phone_number
    if phone_number:
        result = result.replace(' ', '')
        result = result.replace('-', '')
        result = result.replace('.', '')
        result = result.replace('(', '')
        result = result.replace(')', '')
    return result


def get_internal_url(app_mode, url_name, pk, pk_url_kwarg=None):
    """
    Function returns internal URL to the page
    Work only with URL patterns with the same name for both Ops & DoD portals
    :param app_mode:
    :param url_name:
    :param pk:
    :param pk_url_kwarg:
    :return:
    """
    if pk_url_kwarg is None:
        pk_url_kwarg = 'pk'

    namespace = ''
    if app_mode == 'ops_portal':
        namespace = 'admin'
    elif app_mode == 'dod_portal':
        namespace = 'dod'

    return reverse_lazy(f'{namespace}:{url_name}', kwargs={pk_url_kwarg: pk})
