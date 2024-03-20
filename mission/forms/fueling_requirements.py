from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets, BaseModelFormSet, modelformset_factory, FileField

from handling.models import MovementDirection
from mission.models import MissionTurnaround


class MissionFuelingRequirementsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)

        # Disable "No Fuel" checkbox
        self.fields['fuel_required'].empty_label = None
        self.fields['fuel_unit'].empty_label = ''

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def _clean_fields(self):
        for name, bf in self._bound_items():
            field = bf.field
            value = bf.initial if field.disabled else bf.data
            if name == 'fuel_required' and value:
                movement_direction = MovementDirection.objects.filter(code=value[0]).first()
                self.cleaned_data[name] = movement_direction
            else:
                try:
                    if isinstance(field, FileField):
                        value = field.clean(value, bf.initial)
                    else:
                        value = field.clean(value)
                    self.cleaned_data[name] = value
                    if hasattr(self, "clean_%s" % name):
                        value = getattr(self, "clean_%s" % name)()
                        self.cleaned_data[name] = value
                except ValidationError as e:
                    self.add_error(name, e)

    class Meta:
        model = MissionTurnaround
        fields = [
            'fuel_required',
            'fuel_quantity',
            'fuel_unit',
            'fuel_prist_required',
        ]
        widgets = {
            "fuel_required": forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input fuel_required',
            }),
            "fuel_quantity": forms.NumberInput(attrs={
                'class': 'form-control qty-input',
            }),
            "fuel_unit": forms.Select(attrs={
                'class': 'form-control uom-input',
                'data-minimum-input-length': 0,
            }),
            "fuel_prist_required": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class MissionFuelingRequirementsBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.mission:
            self.queryset = MissionTurnaround.objects.filter(
                mission_leg__mission=self.mission)
        else:
            self.queryset = MissionTurnaround.objects.none()

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['mission'] = self.mission
        return kwargs


MissionFuelRequirementsFormSet = modelformset_factory(
    MissionTurnaround,
    extra=0,
    can_delete=False,
    form=MissionFuelingRequirementsForm,
    formset=MissionFuelingRequirementsBaseFormSet,
    fields=[
        'fuel_required',
        'fuel_quantity',
        'fuel_unit',
        'fuel_prist_required',
    ]
)
