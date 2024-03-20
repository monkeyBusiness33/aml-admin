from django.db.models import Func


class CommaSeparatedDecimal(Func):
    template = "TO_CHAR(%(expressions)s, 'FM999,999,999,990.009999999999')"


class CommaSeparatedDecimalRoundTo2(Func):
    template = "TO_CHAR(%(expressions)s, 'FM999,999,999,990.00')"


class CommaSeparatedDecimalOrInteger(Func):
    template = "TRIM(TO_CHAR(%(expressions)s, 'FM999,999,999,990.999999999999'), '.')"


class RegistrationWithoutPunctuation(Func):
    template = "REGEXP_REPLACE(registration, '[^[:alnum:]]*', '', 'g')"
