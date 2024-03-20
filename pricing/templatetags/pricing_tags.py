from django import template


register = template.Library()


@register.filter(name='sort_taxes')
def sort_taxes(value):
    return sorted(value, key=lambda x: ('official' not in x[1], x[0]))
