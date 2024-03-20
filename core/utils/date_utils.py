from datetime import datetime, timedelta


def get_first_and_last_days_of_month(input_date):
    first_day_of_month = datetime(input_date.year, input_date.month, 1)

    if input_date.month == 12:
        last_day_of_month = datetime(input_date.year, input_date.month, 31)
    else:
        last_day_of_month = datetime(input_date.year, input_date.month + 1, 1) + timedelta(days=-1)

    return first_day_of_month, last_day_of_month
