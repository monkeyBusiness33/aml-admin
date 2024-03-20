import re
from django import template
from django.utils.functional import keep_lazy, keep_lazy_text


register = template.Library()


@register.tag
def whitespace_remover(parser, token):
    """
    Remove whitespace within HTML tags,
    including tab, newline and extra space
    characters.

    Example usage::

        {% whitespace_remover %}
            <p class="  test
                        test2
                        test3  ">
                <a href="foo/">Foo</a>
            </p>
        {% end_whitespace_remover %}

    This example returns this HTML::

        <p class="test test2 test3"><a href="foo/">Foo</a></p>

    """
    nodelist = parser.parse(('end_whitespace_remover',))
    parser.delete_first_token()
    return WhitespacelessNode(nodelist)


class WhitespacelessNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return strip_whitespace(self.nodelist.render(context).strip())


@keep_lazy_text
def strip_whitespace(value):
    """
    Return the given HTML with any newlines,
    duplicate whitespace, or trailing spaces
    are removed .
    """
    # Process duplicate whitespace occurrences or
    # *any* newline occurrences and reduce to a single space
    value = re.sub(r'\s{2,}|[\n]+', ' ', str(value))
    # After processing all of the above,
    # any trailing spaces should also be removed
    # Trailing space examples:
    #   - <div >                    Matched by: \s(?=[<>"])
    #   - < div>                    Matched by: (?<=[<>])\s
    #   - <div class="block ">      Matched by: \s(?=[<>"])
    #   - <div class=" block">      Matched by: (?<==\")\s
    #   - <span> text               Matched by: (?<=[<>])\s
    #   - text </span>              Matched by: \s(?=[<>"])
    value = re.sub(r'\s(?=[<>"])|(?<==\")\s|(?<=[<>])\s', '', str(value))
    return value
