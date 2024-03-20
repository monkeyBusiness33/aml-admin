import pytz
from timezonefinder import TimezoneFinder


def get_utc_from_airport_local_time(local_datetime, organisation):
    tf = TimezoneFinder()
    longitude = getattr(organisation, 'longitude')
    latitude = getattr(organisation, 'latitude')

    if longitude and latitude:
        tz = tf.timezone_at(lng=float(longitude),
                            lat=float(latitude))
        location_timezone = pytz.timezone(tz)
        utc_timezone = pytz.UTC

        # Clear existing timezone if it set
        unaware_datetime = local_datetime.replace(tzinfo=None)
        # Apply airport local timezone
        local_datetime_with_timezone = location_timezone.localize(unaware_datetime)
        # Get UTC datetime from airport localised datetime
        datetime_utc = local_datetime_with_timezone.astimezone(utc_timezone)

        return datetime_utc

    # In case if organisation has no longitude and latitude return initial value
    else:
        return local_datetime
