import calendar
import re
from datetime import datetime, date

from django.core.exceptions import ValidationError


def aircard_number_validation(num):
    '''
    This function validate AIR Card number
    '''
    num = num.replace(' ', '')
    if not num.isdigit():
        return False

    data = {}

    for index, digit in enumerate(reversed(num)):
        digit = int(digit)
        if not digit in range(0, 10):
            return False
        if index % 2 == 0:
            data[index] = digit
        else:
            a = digit * 2
            if a > 9:
                digit = a - 9
            else:
                digit = a
            data[index] = digit

    if sum(data.values()) % 10 == 0:
        return True
    else:
        return False


def aircard_number_validation_simple(number, raise_error=True):
    """
    Validate AIR Card numer.
    :param number: AIR Card Number
    :param raise_error:
    :return:
    """
    if number > 99999999:
        if raise_error:
            raise ValidationError('Invalid AIR Card number provided')
        else:
            return False
    return number


def aircard_expiration_validation(air_card_expiration):
    """
    Function validate aircard details
    :param air_card_expiration:
    :return:
    """
    if len(air_card_expiration) > 5:
        return False

    if not re.search('^\d{1,2}/\d{2}$', air_card_expiration):
        return False

    month, year = map(int, air_card_expiration.split('/'))
    year = 2000 + year
    last_day_of_month = calendar.monthrange(year, month)[1]
    expiration = date(year, month, last_day_of_month)

    if datetime.now().date() > expiration:
        return False

    return True
