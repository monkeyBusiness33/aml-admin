from bootstrap_modal_forms.mixins import is_ajax
from django import forms
from django.db import transaction
from django.forms import widgets
from django.core.exceptions import ValidationError
from bootstrap_modal_forms.forms import BSModalModelForm

from aircraft.forms import AircraftTypePickWidget
from aircraft.models import AircraftHistory, Aircraft
from aircraft.utils.registration_duplicate_finder import validate_aircraft_registration
from handling.form_widgets import OrganisationTailNumberDependedPickWidget
from handling.models import HandlingRequest, HandlingRequestDocument, HandlingRequestDocumentFile


class HandlingRequestAircraftForm(BSModalModelForm):

    registration = AircraftHistory.registration.field.formfield(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'onkeyup': 'this.value = this.value.toUpperCase();',
                }),
    )

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)

        if hasattr(self.instance.details, 'pk'):
            aircraft_details = self.instance.details
            self.fields['registration'].initial = aircraft_details.registration

        if self.instance.pk:
            self.fields['type'].disabled = True

        # DoD User restrictions
        dod_selected_position = getattr(self.request, 'dod_selected_position', None)
        if dod_selected_position:
            self.fields['type'].queryset = dod_selected_position.organisation.aircraft_types

    class Meta:
        model = Aircraft
        fields = [
            'asn',
            'registration',
            'type',
            'pax_seats',
        ]

        widgets = {
            'asn': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'type': AircraftTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
                'data-placeholder': 'Select Aircraft Type',
            }),
            'pax_seats': widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        asn = self.cleaned_data['asn']
        aircraft_pk = getattr(self.instance, 'pk', None)
        if asn and Aircraft.objects.filter(asn=asn).exclude(pk=aircraft_pk).exists():
            raise ValidationError({'asn': [
                f'Same ASN is already registered in the database.']})

        return cleaned_data

    def clean_registration(self):
        registration = self.cleaned_data['registration']
        registration = validate_aircraft_registration(registration, self.instance)
        return registration

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def save(self, commit=True):
        aircraft = super().save(commit=False)
        if hasattr(aircraft.details, 'pk'):
            aircraft_details = aircraft.details
        else:
            aircraft_details = AircraftHistory()

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():
                    aircraft.save()

                    aircraft_details.aircraft = aircraft
                    aircraft_details.registration = self.cleaned_data['registration']
                    if self.organisation:
                        aircraft_details.operator = self.organisation
                        aircraft_details.registered_country = self.organisation.details.country
                    aircraft_details.save()

                    self._save_m2m()

                    if aircraft_details.operator.is_military:
                        aircraft_details.operator.aircraft_types.add(aircraft.type, through_defaults={})
            else:
                self.save_m2m = self._save_m2m
        return aircraft


class HandlingRequestConfirmTailNumberForm(BSModalModelForm):
    update_mission = forms.BooleanField(
        label="Update for Whole Mission?",
        required=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )
    asn = Aircraft.asn.field.formfield(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }),
    )

    registration = AircraftHistory.registration.field.formfield(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'onkeyup': 'this.value = this.value.toUpperCase();',
            }),
    )

    type = Aircraft.type.field.formfield(
        required=False,
        widget=AircraftTypePickWidget(attrs={
            'class': 'form-control',
            'data-minimum-input-length': '0',
            'data-placeholder': 'Select Aircraft Type',
        }),
    )

    pax_seats = Aircraft.pax_seats.field.formfield(
        widget=widgets.NumberInput(attrs={
            'class': 'form-control',
        }),
    )

    spf_file = HandlingRequestDocumentFile._meta.get_field('file').formfield(
        label='Upload Signed SPF File',
        required=False,
        widget=widgets.FileInput(
            attrs={
                'class': 'form-control',
            }),
    )

    def __init__(self, *args, **kwargs):
        self.spf_reconcile = kwargs.pop('spf_reconcile', None)
        super().__init__(*args, **kwargs)

        # 'spf_file' field should be visible only in "SPF Reconciled" dialog (which is push spf_reconcile kwarg to form
        if not self.spf_reconcile:
            del self.fields['spf_file']

        organisation = self.instance.customer_organisation
        organisation_fleet = organisation.get_operable_fleet()
        self.fields['tail_number'].queryset = organisation_fleet.filter(aircraft__type=self.instance.aircraft_type)
        self.fields['tail_number'].empty_label = 'Please select Tail Number'

        if not hasattr(self.instance, 'mission_turnaround'):
            del self.fields['update_mission']

    class Meta:
        model = HandlingRequest
        fields = [
            'tail_number',
        ]
        labels = {
            'tail_number': 'Select / Verify Tail Number'
        }

        widgets = {
            "tail_number": OrganisationTailNumberDependedPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        asn = self.cleaned_data['asn']
        aircraft_pk = getattr(self.instance, 'pk', None)
        if asn and Aircraft.objects.filter(asn=asn).exclude(pk=aircraft_pk).exists():
            raise ValidationError({'asn': [
                f'Same ASN is already registered in the database.']})

        return cleaned_data

    def clean_registration(self):
        registration = self.cleaned_data['registration']
        if registration:
            registration = validate_aircraft_registration(registration)
        return registration

    def save(self, commit=True):
        handling_request = super().save(commit=False)
        handling_request.updated_by = self.request.user.person
        handling_request.confirm_tail_number_action = True
        update_mission = self.cleaned_data.get('update_mission', False)
        assigned_tail_number = self.cleaned_data['tail_number']
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():
                    if self.cleaned_data['registration']:
                        aircraft = Aircraft.objects.create(
                            asn=self.cleaned_data['asn'],
                            type=self.cleaned_data['type'],
                            pax_seats=self.cleaned_data['pax_seats'],
                        )
                        aircraft_details = AircraftHistory.objects.create(
                            aircraft=aircraft,
                            registration=self.cleaned_data['registration'],
                            registered_country=handling_request.customer_organisation.details.country,
                            operator=handling_request.customer_organisation,
                        )
                        aircraft.details = aircraft_details
                        aircraft.save()
                        assigned_tail_number = aircraft_details

                        if aircraft_details.operator.is_military:
                            aircraft_details.operator.aircraft_types.add(aircraft.type, through_defaults={})

                    handling_request.tail_number = assigned_tail_number
                    handling_request.aircraft_type = assigned_tail_number.aircraft.type
                    handling_request.save()

                    if hasattr(self.instance, 'mission_turnaround'):
                        mission = handling_request.mission_turnaround.mission_leg.mission
                        mission.meta_is_partial_save = True
                        mission.updated_by = handling_request.updated_by
                        mission_leg = handling_request.mission_turnaround.mission_leg
                        mission_leg.prevent_mission_update = True
                        mission_leg.updated_by = handling_request.updated_by

                        if update_mission:
                            mission.aircraft = handling_request.tail_number
                            mission.aircraft_type = handling_request.tail_number.aircraft.type
                            mission.save()

                            mission_leg.aircraft_override = None
                            mission_leg.aircraft_type_override = None
                            mission_leg.save()
                        else:
                            mission_leg.aircraft_override = handling_request.tail_number
                            mission_leg.aircraft_type_override = handling_request.tail_number.aircraft.type
                            mission_leg.save()

        return handling_request
