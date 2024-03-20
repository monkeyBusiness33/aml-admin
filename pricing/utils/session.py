import re


def serialize_request_data(request_data):
    """
    When request.POST data is serialized to be stored in session, multiple-select field values are not
    stored properly (only the last value from list is stored). The code already expects strings instead
    of lists in many places, so here we ensure that only the mutliple-choice fields are stored as lists.
    """
    MULTIPLE_CHOICE_FIELD_NAMES = [
        r'-inclusive_taxes$',
        r'-delivery_methods$',
    ]

    return {k: (v if any(re.search(pattern, k) for pattern in MULTIPLE_CHOICE_FIELD_NAMES) else v[0])
            for k, v in request_data.lists()}
