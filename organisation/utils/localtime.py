import pytz


def get_airport_local_time_from_utc(utc_datetime, organisation):
    location_timezone = organisation.pytz_timezone

    # In case if organisation has no longitude and latitude return initial value
    if not location_timezone:
        return utc_datetime

    # Get Local datetime from UTC datetime
    return utc_datetime.astimezone(location_timezone)
