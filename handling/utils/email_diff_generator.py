import decimal
import logging

from django.db.models import F
from django.forms.models import model_to_dict
from dateutil.parser import parse, ParserError
from datetime import datetime, date

from aircraft.models import AircraftType, AircraftHistory
from core.models import UnitOfMeasurement
from organisation.models import Organisation

logger = logging.getLogger(__name__)


def get_fields(instance):
    """
    Helper function to return instance fields with additional filtering
    :param instance:
    :return:
    """
    my_model_fields = instance._meta.get_fields()
    ignored_fields = ['air_card_photo']
    fields = []

    for field in my_model_fields:
        if not field.one_to_one and not field.one_to_many and not field.many_to_many and field.name not in ignored_fields:
            fields.append(field.name)

    return fields


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError("Type %s not serializable" % type(obj))


def get_movement_services_diffs(services, value_type, diffs=None, debug=False):
    initial_run = True if diffs is None else False
    if diffs is None:
        diffs = {}
    if debug:
        print('services', services)
        print('diffs', diffs)

    for service in services:
        if not initial_run:
            if service['id'] not in diffs:
                diffs.setdefault(service['id'], {}).update({'added': True})
        for field_name, field_value in service.items():
            if field_name == 'name':
                diffs.setdefault(service['id'], {}).update({field_name: field_value})
            elif field_name in ['note', 'booking_text', 'booking_quantity', 'booking_quantity_uom_id']:
                diffs.setdefault(service['id'], {}).setdefault(field_name, {}).update({value_type: field_value})

    for diff_id in diffs:
        if not services.filter(pk=diff_id).exists():
            diffs.setdefault(diff_id, {}).update({'removed': True})
    return diffs


def generate_diff_dict(handling_request, existing_amendment_data=None):
    """
    This function creates dictionary with differences of two HandlingRequest objects
    First time it should be called only with 'handling_request' argument to create initial state (old values)
    second time it should be called with 'existing_amendment_data' which is output of first function call.
    Final result should be serialized to json (if needed) and submitted as argument to the Celery emailing function
    and should be used to initialize object based on the HandlingRequestDiff class
    :param handling_request: HandlingRequest object
    :param existing_amendment_data:
    :return:
    """
    if not existing_amendment_data:
        amendments = {}
        arrival_movement = {}
        departure_movement = {}
        value_type = 'old_value'
    else:
        amendments = existing_amendment_data
        arrival_movement = existing_amendment_data['arrival_movement']
        departure_movement = existing_amendment_data['departure_movement']
        value_type = 'new_value'

    if not handling_request or not handling_request.arrival_movement or not handling_request.departure_movement:
        logger.warning('S&F Request Diff Generator: No sufficient data to create diff')
        return

    handling_request_dict = model_to_dict(handling_request, fields=get_fields(handling_request))
    for field_name, field_value in handling_request_dict.items():
        amendments.setdefault(field_name, {}).update({value_type: field_value})

    # Arrival Movement Diff Processing
    arrival_movement_dict = model_to_dict(handling_request.arrival_movement,
                                          fields=get_fields(handling_request.arrival_movement))
    for field_name, field_value in arrival_movement_dict.items():
        arrival_movement.setdefault(field_name, {}).update({value_type: field_value})
    amendments['arrival_movement'] = arrival_movement

    # Arrival Services Diff Processing
    arrival_services_values = handling_request.arrival_movement.hr_services.values(
        'id', 'note', 'booking_text', 'booking_quantity', 'booking_quantity_uom_id', name=F('service__name'))

    if existing_amendment_data:
        existing_services = existing_amendment_data['arrival_movement']['services']
        amendments['arrival_movement']['services'] = get_movement_services_diffs(arrival_services_values,
                                                                                 value_type, existing_services)
    else:
        amendments['arrival_movement']['services'] = get_movement_services_diffs(arrival_services_values, value_type)

    # Departure Movement Diff Processing
    departure_movement_dict = model_to_dict(handling_request.departure_movement,
                                            fields=get_fields(handling_request.departure_movement))
    for field_name, field_value in departure_movement_dict.items():
        departure_movement.setdefault(field_name, {}).update({value_type: field_value})
    amendments['departure_movement'] = departure_movement

    # Departure Services Diff Processing
    departure_services_values = handling_request.departure_movement.hr_services.values(
        'id', 'note', 'booking_text', 'booking_quantity', 'booking_quantity_uom_id', name=F('service__name'),
    )
    if existing_amendment_data:
        existing_services = existing_amendment_data['departure_movement']['services']
        amendments['departure_movement']['services'] = get_movement_services_diffs(departure_services_values,
                                                                                   value_type, existing_services)
    else:
        amendments['departure_movement']['services'] = get_movement_services_diffs(departure_services_values,
                                                                                   value_type)

    return amendments


class DiffValue:
    old_value = None
    new_value = None
    is_different = False

    def __init__(self, old_value, new_value):
        setattr(self, 'old_value', old_value)
        setattr(self, 'new_value', new_value)

        if old_value != new_value:
            self.is_different = True

    def __str__(self):
        return f'{self.new_value}'

    __repr__ = __str__

    @property
    def value(self):
        if self.new_value is None:
            if self.is_different:
                return self.new_value
            else:
                return self.old_value
        else:
            return self.new_value


class HandlingRequestServiceDiff:
    removed = None
    added = None

    name = None
    note = None
    booking_text = None
    booking_quantity = None
    booking_quantity_uom_id = None

    def __init__(self, in_dict: dict):
        for key, value in in_dict.items():
            if key in ['id', 'name', 'added', 'removed']:
                value = value
            elif key == 'booking_quantity_uom_id':
                old_value = ''
                new_value = ''
                old_value_obj = UnitOfMeasurement.objects.filter(pk=value.get('old_value')).first()
                if old_value_obj:
                    old_value = old_value_obj.description_plural
                new_value_obj = UnitOfMeasurement.objects.filter(pk=value.get('new_value')).first()
                if new_value_obj:
                    new_value = new_value_obj.description_plural
                value = DiffValue(old_value, new_value)
            else:
                value = DiffValue(value.get('old_value'), value.get('new_value'))
            setattr(self, key, value)

    def html_repr(self):
        css_class = ''
        details = []
        if self.added:
            css_class = 'value-added'
        elif self.removed:
            css_class = 'value-updated-crossed'

        if self.note.is_different or self.booking_text.is_different or self.booking_quantity.is_different:
            css_class = 'value-updated'

        html = f'<span class="{css_class}"><b>{self.name}</b></span>'

        if self.note.value:
            value_css_class = 'value-updated' if self.note.is_different else ''
            html_value = f'<span class="{value_css_class}">{self.note.value}</span>'
            details.append(html_value)
        if self.booking_text.value:
            value_css_class = 'value-updated' if self.booking_text.is_different else ''
            html_value = f'<span class="{value_css_class}">{self.booking_text.value}</span>'
            details.append(html_value)
        if self.booking_quantity.value:
            value_css_class = 'value-updated' if self.booking_quantity.is_different else ''
            html_value = (f'<span class="{value_css_class}">{self.booking_quantity.value} '
                          f'{self.booking_quantity_uom_id.value if self.booking_quantity_uom_id else ""}</span>')
            details.append(html_value)

        # Open scope
        if details:
            html += ' ('
            for detail in details:
                html += detail
                if detail == details[-1]:
                    html += ')'
                else:
                    html += ', '
        return html


class HandlingRequestMovementDiff:
    services = []

    def __init__(self, in_dict: dict):
        services_list = in_dict.pop('services')
        self.services = []
        for service_id, service_details in services_list.items():
            self.services.append(HandlingRequestServiceDiff(in_dict=service_details))

        def passengers_repr(is_passengers_onboard, is_passengers_tbc, passengers):
            if not is_passengers_onboard:
                return 'No Passengers'
            else:
                if is_passengers_tbc:
                    return 'TBC'
                else:
                    return str(passengers)

        for key, value in in_dict.items():
            if key == 'date':
                try:
                    old_value_obj = parse(value['old_value']) if not isinstance(value['old_value'], datetime) else value['old_value']
                    new_value_obj = parse(value['new_value']) if not isinstance(value['new_value'], datetime) else value['new_value']
                    obj = DiffValue(old_value_obj, new_value_obj)
                    setattr(self, 'date', obj)
                except ParserError:
                    pass
            elif key == 'airport':
                old_value_obj = Organisation.objects.filter(pk=value['old_value']).first()
                new_value_obj = Organisation.objects.filter(pk=value['new_value']).first()
                obj = DiffValue(old_value_obj, new_value_obj)
                setattr(self, 'airport', obj)
            else:
                setattr(self, key, DiffValue(value['old_value'], value['new_value']))

        # Assemble passengers value from parts
        old_passengers_value = passengers_repr(self.is_passengers_onboard.old_value,
                                               self.is_passengers_tbc.old_value,
                                               self.passengers.old_value)
        new_passengers_value = passengers_repr(self.is_passengers_onboard.new_value,
                                               self.is_passengers_tbc.new_value,
                                               self.passengers.new_value)
        setattr(self, 'passengers', DiffValue(old_passengers_value, new_passengers_value))

    @property
    def is_date_date_different(self):
        return self.date.old_value.date() != self.date.new_value.date()


class HandlingRequestDiff:
    """
    This class should be initialized using output from the generate_diff_dict function, it creates some kind of
    HandlingRequest object with its fields, old and new values.
    This object could be used in the email templates to display difference for changed requests.
    """
    arrival_movement = None
    departure_movement = None
    tail_number = None

    def __init__(self, in_dict: dict):
        from handling.models import MovementDirection
        arrival_movement = in_dict.pop('arrival_movement')
        departure_movement = in_dict.pop('departure_movement')
        setattr(self, 'arrival_movement', HandlingRequestMovementDiff(in_dict=arrival_movement))
        setattr(self, 'departure_movement', HandlingRequestMovementDiff(in_dict=departure_movement))

        for key, value in in_dict.items():
            if key == 'airport':
                old_value_obj = Organisation.objects.filter(pk=value['old_value']).first()
                new_value_obj = Organisation.objects.filter(pk=value['new_value']).first()
                obj = DiffValue(old_value_obj, new_value_obj)
                setattr(self, 'airport', obj)
            elif key == 'tail_number':
                old_value_obj = AircraftHistory.objects.filter(pk=value['old_value']).first()
                new_value_obj = AircraftHistory.objects.filter(pk=value['new_value']).first()
                obj = DiffValue(old_value_obj, new_value_obj)
                setattr(self, 'tail_number', obj)
            elif key == 'aircraft_type':
                old_value_obj = AircraftType.objects.filter(pk=value['old_value']).first()
                new_value_obj = AircraftType.objects.filter(pk=value['new_value']).first()
                obj = DiffValue(old_value_obj, new_value_obj)
                setattr(self, 'aircraft_type', obj)
            elif key == 'fuel_required':
                old_value_obj = MovementDirection.objects.filter(pk=value['old_value']).first()
                new_value_obj = MovementDirection.objects.filter(pk=value['new_value']).first()
                obj = DiffValue(old_value_obj, new_value_obj)
                setattr(self, 'fuel_required', obj)
            elif key == 'fuel_unit':
                old_value_obj = UnitOfMeasurement.objects.filter(pk=value['old_value']).first()
                new_value_obj = UnitOfMeasurement.objects.filter(pk=value['new_value']).first()
                obj = DiffValue(old_value_obj, new_value_obj)
                setattr(self, 'fuel_unit', obj)
            else:
                setattr(self, key, DiffValue(value['old_value'], value['new_value']))
