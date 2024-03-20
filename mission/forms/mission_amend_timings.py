from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.db.models import When, Case, Value
from django.forms.widgets import ChoiceWidget
from django.utils import timezone
from django_flatpickr.schemas import FlatpickrOptions
from django_flatpickr.widgets import DateTimePickerInput

from django_select2 import forms as s2forms
from django.forms import widgets, ChoiceField


class MissionLegToAmendSelectWidget(s2forms.Select2Widget, ChoiceWidget):

    def valid_value(self, value):
        """Check to see if the provided value is a valid choice."""
        text_value = str(value)
        for k, v, _ in self.choices:
            if isinstance(v, (list, tuple)):
                # This is an optgroup, so look inside the group for options
                for k2, v2 in v:
                    if value == k2 or text_value == str(k2):
                        return True
            else:
                if value == k or text_value == str(k):
                    return True
        return False

    @staticmethod
    def _choice_has_empty_value(choice):
        """Return True if the choice's value is empty string or None."""
        value, _, is_disabled = choice
        return value is None or value == ""

    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget."""
        groups = []
        has_selected = False

        for index, (option_value, option_label, is_disabled) in enumerate(self.choices):
            if not attrs:
                attrs = {}
            attrs['is_disabled'] = is_disabled
            if option_value is None:
                option_value = ""

            subgroup = []
            if isinstance(option_label, (list, tuple)):
                group_name = option_value
                subindex = 0
                choices = option_label
            else:
                group_name = None
                subindex = None
                choices = [(option_value, option_label)]
            groups.append((group_name, subgroup, index))

            for subvalue, sublabel in choices:
                selected = (not has_selected or self.allow_multiple_selected) and str(
                    subvalue
                ) in value
                has_selected |= selected
                subgroup.append(
                    self.create_option(
                        name,
                        subvalue,
                        sublabel,
                        selected,
                        index,
                        subindex=subindex,
                        attrs=attrs,
                    )
                )
                if subindex is not None:
                    subindex += 1
        return groups

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        index = str(index) if subindex is None else "%s_%s" % (index, subindex)
        option_attrs = (
            self.build_attrs(self.attrs, attrs) if self.option_inherits_attrs else {}
        )
        if selected:
            option_attrs.update(self.checked_attribute)
        if "id" in option_attrs:
            option_attrs["id"] = self.id_for_label(option_attrs["id"], index)
        if attrs['is_disabled'] == 'true':
            option_attrs['disabled'] = ''

        return {
            "name": name,
            "value": value,
            "label": label,
            "selected": selected,
            "index": index,
            "attrs": option_attrs,
            "type": self.input_type,
            "template_name": self.option_template_name,
            "wrap_label": True,
        }


class MissionLegToAmendMovementSelectWidget(s2forms.Select2Widget, ChoiceWidget):

    @staticmethod
    def _choice_has_empty_value(choice):
        """Return True if the choice's value is empty string or None."""
        value, _, mission_leg, original_datetime = choice
        return value is None or value == ""

    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget."""
        groups = []
        has_selected = False

        for index, (option_value, option_label, mission_leg, original_datetime) in enumerate(self.choices):
            if not attrs:
                attrs = {}
            attrs['mission_leg'] = mission_leg
            attrs['original_datetime'] = original_datetime
            if option_value is None:
                option_value = ""

            subgroup = []
            if isinstance(option_label, (list, tuple)):
                group_name = option_value
                subindex = 0
                choices = option_label
            else:
                group_name = None
                subindex = None
                choices = [(option_value, option_label)]
            groups.append((group_name, subgroup, index))

            for subvalue, sublabel in choices:
                selected = (not has_selected or self.allow_multiple_selected) and str(
                    subvalue
                ) in value
                has_selected |= selected
                subgroup.append(
                    self.create_option(
                        name,
                        subvalue,
                        sublabel,
                        selected,
                        index,
                        subindex=subindex,
                        attrs=attrs,
                    )
                )
                if subindex is not None:
                    subindex += 1
        return groups

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        index = str(index) if subindex is None else "%s_%s" % (index, subindex)
        option_attrs = (
            self.build_attrs(self.attrs, attrs) if self.option_inherits_attrs else {}
        )
        if selected:
            option_attrs.update(self.checked_attribute)
        if "id" in option_attrs:
            option_attrs["id"] = self.id_for_label(option_attrs["id"], index)

        option_attrs['mission_leg'] = attrs['mission_leg']
        option_attrs['original_datetime'] = attrs['original_datetime']

        return {
            "name": name,
            "value": value,
            "label": label,
            "selected": selected,
            "index": index,
            "attrs": option_attrs,
            "type": self.input_type,
            "template_name": self.option_template_name,
            "wrap_label": True,
        }


class MissionAmendTimingsChoiceField(ChoiceField):
    def valid_value(self, value):
        """Check to see if the provided value is a valid choice."""
        text_value = str(value)
        for k, v, *_ in self.choices:
            if isinstance(v, (list, tuple)):
                # This is an optgroup, so look inside the group for options
                for k2, v2 in v:
                    if value == k2 or text_value == str(k2):
                        return True
            else:
                if value == k or text_value == str(k):
                    return True
        return False


class MissionAmendTimingsForm(BSModalForm):
    mission_leg_to_amend = MissionAmendTimingsChoiceField(
        label='Mission Leg To Amend',
        widget=MissionLegToAmendSelectWidget(attrs={
            'class': 'form-control',
        })
    )
    movement_to_amend = MissionAmendTimingsChoiceField(
        label='Movement To Amend',
        widget=MissionLegToAmendMovementSelectWidget(attrs={
            'class': 'form-control',
        })
    )
    new_datetime = forms.DateTimeField(
        label='New Movement Date & Time',
        widget=DateTimePickerInput(
            attrs={'class': 'form-control'},
        )
    )
    movement_changed_by = forms.CharField(
        label='Movement changed By',
        required=False,
        disabled=True,
        widget=widgets.TextInput(
            attrs={'class': 'form-control'},
        )
    )
    roll_change_to_subsequent_legs = forms.BooleanField(
        label='Roll Change to All Subsequent Mission Legs?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)

        mission_leg_to_amend_qs = self.mission.active_legs.annotate(is_disabled=Case(
            When(arrival_datetime__lt=timezone.now(), then=Value('true')),
            default=Value('false')
        ))
        mission_leg_to_amend_choices = []
        for mission_leg in mission_leg_to_amend_qs:
            mission_leg_to_amend_choices.append((mission_leg.pk,
                                                 f'Flight Leg {mission_leg.sequence_id} - {mission_leg}',
                                                 mission_leg.is_disabled))
        mission_leg_to_amend_choices.insert(0, (None, 'Please select Flight Leg', 0))
        self.fields['mission_leg_to_amend'].choices = mission_leg_to_amend_choices

        movement_to_amend_choices = []
        for mission_leg in self.mission.active_legs:
            departure = (f'leg_{mission_leg.pk}_departure',
                         f'Departure - {mission_leg.departure_datetime.strftime("%b-%d-%Y %H:%MZ").upper()}',
                         mission_leg.pk,
                         mission_leg.departure_datetime.strftime("%Y-%m-%d %H:%M"),
                         )
            arrival = (f'leg_{mission_leg.pk}_arrival',
                       f'Arrival - {mission_leg.arrival_datetime.strftime("%b-%d-%Y %H:%MZ").upper()}',
                       mission_leg.pk,
                       mission_leg.arrival_datetime.strftime("%Y-%m-%d %H:%M"),
                       )
            movement_to_amend_choices.append(departure)
            movement_to_amend_choices.append(arrival)
        movement_to_amend_choices.insert(0, (None, 'Please select Movement', 0, 0))
        self.fields['movement_to_amend'].choices = movement_to_amend_choices

        new_datetime_options = FlatpickrOptions(
            static=False,
            allowInput=False,
        )
        self.fields['new_datetime'].widget = DateTimePickerInput(
            attrs={'class': 'form-control'},
            options=new_datetime_options,
        )

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid
