from django.forms.models import ModelChoiceField
from django.core.exceptions import ValidationError
from django.db import models
from django import forms


class Select2ToFieldModelChoiceField(ModelChoiceField):
    """
    Modifications on top of the ModelChoiceField for the
    django-select2 widget to select fields with the to_field option
    """
    def prepare_value(self, value):
        if hasattr(value, '_meta'):
            if self.to_field_name:
                return value.pk
            else:
                return value.pk
        return super().prepare_value(value)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            key = self.to_field_name or 'pk'
            if isinstance(value, self.queryset.model):
                value = getattr(value, key)
            value = self.queryset.get(**{'pk': value})
            value = value
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')

        return value


def validate_csv(data):
    return all([isinstance(i, int) for i in data])


DAY_CHOICES = (
    (1, "Monday"),
    (2, "Tuesday"),
    (3, "Wednesday"),
    (4, "Thursday"),
    (5, "Friday"),
    (6, "Saturday"),
    (7, "Sunday")
)


class WeekdayFormField(forms.TypedMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs:
            kwargs['choices'] = DAY_CHOICES
        kwargs.pop('max_length', None)
        if 'widget' not in kwargs:
            kwargs['widget'] = forms.widgets.SelectMultiple
        super(WeekdayFormField, self).__init__(*args, **kwargs)

    def prepare_value(self, value):
        if value:
            value = [int(x) for x in value.strip('[]').split(',') if x]
        else:
            value = []
        return value


class WeekdayField(models.CharField):
    """
    Field to simplify the handling of a multiple choice of None->all days.
    """

    description = "Weekday Field"
    default_validators = [validate_csv]

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 14
        super(WeekdayField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        return super(WeekdayField, self).formfield(form_class=WeekdayFormField, **kwargs)

    def to_python(self, value):
        if isinstance(value, str):
            if value:
                value = [int(x) for x in value.strip('[]').split(',') if x]
            else:
                value = []
        return value

    def get_db_prep_value(self, value, connection=None, prepared=False):
        return ",".join([str(x) for x in value or []])
