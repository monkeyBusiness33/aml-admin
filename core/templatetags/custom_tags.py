from django import template
register = template.Library()


@register.simple_tag(name='any_has_prop_with_value')
def any_has_prop_with_value(items_list, prop, value):
    return any([getattr(item, prop, False) == value for item in items_list])
