from django import template
register = template.Library()


@register.filter(takes_context=True)
def person_position_in(person, organisation):
    """
    Template tag return Person Position for the given organisation
    :param person: Person object
    :param organisation: Organisation object
    :return: OrganisationPeople object
    """
    if person:
        return person.organisation_people.filter(
            organisation=organisation).first()
    else:
        return None


@register.filter(takes_context=True)
def is_handling_request_editable(handling_request, user=None):
    return handling_request.is_request_editable(user)
