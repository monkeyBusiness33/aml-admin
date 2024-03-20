from django.utils.safestring import mark_safe
from django import template

from core.utils.datatables_functions import get_datatable_clipped_value

register = template.Library()


@register.filter(takes_context=True)
def is_url_name_in(resolver_url_name, url_list):
    """
    Template filter for the highlighting active sidebar items
    :param resolver_url_name:
    :param url_list:
    :return:
    """
    url_list = url_list.split(",")
    if not resolver_url_name:
        resolver_url_name = ''

    return True if resolver_url_name in url_list else False


@register.filter(takes_context=True)
def is_url_name_contained_in(resolver_url_name, url_list):
    """
    Same as the above template filter, but looks for partial matches
    """
    url_list = url_list.split(",")
    if not resolver_url_name:
        resolver_url_name = ''
    return any(substring in resolver_url_name for substring in url_list)


@register.filter
def is_formset_has_errors(formset_errors: list, fields: str):
    """
    This filter return boolean value for formset object of one of specified forms has errors
    :param formset_errors: formset object
    :param fields: comma separated string, field names
    :return:
    """
    if not formset_errors:
        formset_errors = []
    fields_list = fields.split(",")
    for error_dict in formset_errors:
        for field_name in fields_list:
            if field_name in error_dict:
                return True
    return False


@register.filter
def get_form_field(form, field):
    return form[field]

@register.filter
def get_form_field_errors(form, field):
    return form[field].errors

@register.filter(name='times')
def times(number):
    return range(number)

@register.filter
def normalize(value):
    formatted_value = value.normalize()
    return "{:f}".format(formatted_value)


@register.filter
def get_formset_errors(formset, num):
    return formset[num].errors


@register.filter(is_safe=True)
def yesno_icon(value):
    """
    Copy of the default Django's 'yesno' filer but modified to echo icons
    """

    if value is None:
        icon_name = 'fa-minus'
        icon_color = 'text-primary'
        icon_text = 'N/A'
    elif value:
        icon_name = 'fa-check-circle'
        icon_color = 'text-success'
        icon_text = 'Yes'
    else:
        icon_name = 'fa-ban'
        icon_color = 'text-danger'
        icon_text = 'No'

    html = f'<i class="fas {icon_name} {icon_color}" data-bs-toggle="tooltip" data-bs-placement="top" ' \
           f'title="{icon_text}"></i>'
    return mark_safe(html)


@register.filter(is_safe=True)
def clipped_text(value, max_length=15):
    html = get_datatable_clipped_value(text=value, max_length=max_length)
    return mark_safe(html)


@register.filter
def get_form_field(form, field):
    return form[field]


@register.filter
def get_form_field_errors(form, field):
    return form[field].errors


@register.filter(name='times')
def times(number):
    return range(number)


@register.filter
def normalize(value):
    formatted_value = value.normalize()
    return "{:f}".format(formatted_value)


@register.filter
def get_formset_errors(formset, num):
    return formset[num].errors
