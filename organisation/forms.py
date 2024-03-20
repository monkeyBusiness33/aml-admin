import re
from collections import Counter

from django.db.models import Count, Subquery, Max, Min, Q, F, Value, CharField, IntegerField, BooleanField, DateField, Case, When, OuterRef, Exists
from django.forms import BaseModelFormSet, ValidationError, formset_factory, modelformset_factory
from core.form_widgets import CountryPickWidget, FuelTypesPickWidget, TagPickCreateWidget
from bootstrap_modal_forms.mixins import CreateUpdateAjaxMixin, PopRequestMixin
from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax

from handling.models import HandlingService
from organisation.form_widgets import AirportPickWidget, AirportsPickWidget, OrganisationPersonPickWidget, \
    OrganisationPickWidget, DlaServicePickWidget, OrganisationWithTypePickWidget
from django import forms
from django.forms import widgets
from django_select2 import forms as s2forms
from user.models import Person
from user.form_widgets import PersonTitlePickWidget
from user.models.person import PersonDetails, PersonTitle
from .models import *
from organisation.form_widgets import GroundServicesPickWidget, HandlerTypePickWidget, NasdTypePickWidget, \
    OperatorAuthorisedPeoplePickWidget, OperatorPreferredHandlerDependentPickWidget, OperatorTypePickWidget, \
    OrganisationAircraftTypesPickWidget, OrganisationDocumentTypePickWidget, OrganisationRolePickWidget, \
    OrganisationTypePickWidget, OrganisationTypesPickWidget, ServiceProviderLocationPickWidget
from core.form_widgets import CurrencyPickWidget
from django.db import transaction


class HandlingServicePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class OrganisationPeopleRolePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class OrganisationTypeSelectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].queryset = self.fields['type'].queryset.filter(
            pk__in=[1, 2, 3, 4, 5, 11, 14, 1002, ]
        )

    class Meta:
        model = OrganisationDetails
        fields = ['type', ]
        widgets = {
            "type": OrganisationTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class OrganisationAircraftTypesForm(forms.ModelForm):

    class Meta:
        model = Organisation
        fields = ['aircraft_types', ]
        widgets = {
            "aircraft_types": OrganisationAircraftTypesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class OrganisationDetailsForm(forms.ModelForm):
    secondary_types = forms.ModelMultipleChoiceField(
        label='Secondary Type(s)',
        queryset=OrganisationType.objects.secondary_types(),
        required=False,
        widget=OrganisationTypesPickWidget(attrs={
            'class': 'form-control',
            'data-minimum-input-length': 0,
            'data-placeholder': 'Please Select Secondary Types',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context', None)
        self.page_org_type = kwargs.pop('page_org_type', None)
        super().__init__(*args, **kwargs)

        self.fields['department_of'].empty_label = 'Type Organisation Name'
        self.fields['type'].label = 'Primary Type'

        # During edition primary typa can't be changed; Create From Person handles type creation with separate form
        if self.context in ('Edit', 'create_from_person') or self.page_org_type:
            self.fields['type'].disabled = True

    class Meta:
        model = OrganisationDetails
        fields = [
            'registered_name',
            'trading_name',
            'department_of',
            'country',
            'tax_number',
            'type',
            'secondary_types',
            'supplier_organisation',
        ]

        widgets = {
            "registered_name": widgets.TextInput(attrs={
                'class': 'form-control search-for-duplicate',
                'data-search-term': 'term',
                'autocomplete': 'off',
            }),
            "trading_name": widgets.TextInput(attrs={
                'class': 'form-control search-for-duplicate',
                'data-search-term': 'term',
                'autocomplete': 'off',
            }),
            "department_of": OrganisationWithTypePickWidget(attrs={
                'class': 'form-control',
            }),
            "country": CountryPickWidget(attrs={
                'class': 'form-control',
            }),
            "tax_number": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "type": OrganisationTypePickWidget(
                # Exclude types that need details but can't be edited now (Airports, DAOs)
                queryset=OrganisationType.objects.filter(pk__in=[1, 2, 3, 4, 5, 11, 14, 1002, ]),
                attrs={
                    'class': 'form-control',
                    'data-minimum-input-length': 0,
                    'data-placeholder': 'Please Select the Primary Type',
                }),
            "supplier_organisation": OrganisationWithTypePickWidget(attrs={
                'class': 'form-control',
            }),
        }


class OrganisationTypesSelectForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    class Meta:
        model = OrganisationDetails
        fields = []


class FuelResellerDetailsForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)
        if hasattr(self.organisation, 'details'):
            organisation_type = getattr(self.organisation.details, 'type')
            if organisation_type.id == 13:
                self.fields['is_fuel_agent'].initial = True

    is_fuel_agent = forms.BooleanField(required=False,
                                       initial=False,
                                       label='Acts as an agent for its customers?',
                                       widget=widgets.CheckboxInput(
                                           attrs={
                                               'class': 'form-check-input d-block',
                                           }),
                                       )


class OrganisationRestictedForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['invoiceable_organisation'].empty_label = 'Type Organisation Name'

    class Meta:
        model = OrganisationRestricted
        fields = ['invoiceable_organisation',
                  'is_customer', 'is_fuel_seller', 'is_service_supplier',
                  'is_competitor', 'is_invoiceable',
                  ]
        widgets = {
            "invoiceable_organisation": OrganisationPickWidget(attrs={
                'class': 'form-control',
            }),
            "is_customer": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_fuel_seller": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_service_supplier": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_competitor": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_invoiceable": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
        }


class OperatorDetailsForm(forms.ModelForm):
    authorising_people = forms.ModelMultipleChoiceField(
        label='Authorizing Officer',
        required=False,
        queryset=OrganisationPeople.objects.none(),
        widget=OperatorAuthorisedPeoplePickWidget(attrs={
            'class': 'form-control',
            'data-minimum-input-length': 0,
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if self.instance.organisation.pk:
                self.fields['authorising_people'].queryset = self.instance.organisation.organisation_people.all()
                self.fields['authorising_people'].label = self.instance.organisation.authorising_person_role_name
                self.fields['authorising_people'].initial = self.instance.organisation.organisation_people.filter(
                    is_authorising_person=True)
        else:
            self.fields['authorising_people'].disabled = True

    class Meta:
        model = OperatorDetails
        fields = ['contact_email', 'contact_phone',
                  'commercial_email', 'commercial_phone',
                  'ops_email', 'ops_phone', 'type',
                  ]
        widgets = {
            "contact_email": widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            "contact_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "commercial_email": widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            "commercial_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "ops_email": widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            "ops_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "type": OperatorTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class OrganisationAddressForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['airport'].empty_label = 'Type Airport Name/ICAO/IATA'

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationAddress
        fields = ['line_1', 'line_2', 'line_3',
                  'town_city', 'state', 'post_zip_code',
                  'country', 'airport',
                  'email', 'phone', 'fax',
                  'is_primary_address', 'is_postal_address',
                  'is_physical_address', 'is_billing_address',
                  ]
        widgets = {
            "line_1": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),
            "line_2": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),
            "line_3": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),

            "town_city": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),
            "state": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),
            "post_zip_code": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),

            "country": CountryPickWidget(attrs={
                'class': 'form-control'
            }),
            "airport": AirportPickWidget(attrs={
                'class': 'form-control'
            }),

            "email": widgets.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),
            "phone": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),
            "fax": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '',
            }),

            "is_primary_address": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_postal_address": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_physical_address": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_billing_address": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
        }


class OrganisationAddressBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        self.first_required = kwargs.pop('first_required', False)
        super().__init__(*args, **kwargs)
        if self.organisation:
            self.queryset = OrganisationAddress.objects.filter(
                organisation=self.organisation).all()
        else:
            self.queryset = OrganisationAddress.objects.none()
        # Make required first form in formset
        if self.first_required:
            self.forms[0].empty_permitted = False
            for field in self.forms[0].fields:
                field_required_flag = self.forms[0].fields[field].required
                if field_required_flag == True:
                    self.forms[0].fields[field].widget.attrs['required'] = 'required'



OrganisationAddressFormSet = modelformset_factory(
    OrganisationAddress,
    extra=4,
    can_delete=True,
    form=OrganisationAddressForm,
    formset=OrganisationAddressBaseFormSet,
    fields=['line_1', 'line_2', 'line_3',
            'town_city', 'state', 'post_zip_code',
            'country', 'airport',
            'email', 'phone', 'fax',
            'is_primary_address', 'is_postal_address',
            'is_physical_address', 'is_billing_address',
            ]
)


class OrganisationTagsForm(BSModalModelForm):

    class Meta:
        model = Organisation
        fields = ['tags', ]
        widgets = {
            "tags": TagPickCreateWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class OrganisationPersonForm(BSModalModelForm):
    '''
    Form for Organisation Person creation
    '''

    role = OrganisationPeople.role.field.formfield(
        widget=OrganisationPeopleRolePickWidget(
            attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
                }),
    )

    job_title = OrganisationPeople.job_title.field.formfield(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}),
    )

    position_email = OrganisationPeople.contact_email.field.formfield(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)

        if self.organisation:
            self.fields['title'].queryset = PersonTitle.objects.filter(
                Q(organisation=None) | Q(organisation=self.organisation)
            )
            self.fields['title'].empty_label = 'Pick Person Title'

            person_current_role_codename = None
            if hasattr(self.instance, 'person'):
                organisation_people = OrganisationPeople.objects.get(person=self.instance.person,
                                                                     organisation=self.organisation)
                self.fields['role'].initial = organisation_people.role
                person_current_role_codename = organisation_people.role.code_name
                self.fields['job_title'].initial = organisation_people.job_title
                self.fields['position_email'].initial = organisation_people.contact_email

            role_qs = self.fields['role'].queryset

        # Make personal email optional in quick create, and use the same
        self.fields['contact_email'].required = False

    def save(self, commit=True):
        person_details = super().save(commit=False)

        if hasattr(person_details, 'person'):
            person = person_details.person
            organisation_people = OrganisationPeople.objects.get(person=person,
                                                organisation=self.organisation)
        else:
            person = Person()
            organisation_people = OrganisationPeople(person=person,
                                                    organisation=self.organisation)

        # Fill organisation_people object fields
        organisation_people.role = self.cleaned_data['role']
        organisation_people.job_title = self.cleaned_data['job_title']
        organisation_people.contact_email = self.cleaned_data['position_email']

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            from django.db import transaction

            if commit:
                with (transaction.atomic()):
                    person.save()

                    person_details.person = person

                    # Use the work email to populate personal email if not provided
                    if self.cleaned_data['contact_email']:
                        person_details.contact_email = self.cleaned_data['contact_email']
                    else:
                        person_details.contact_email = organisation_people.contact_email

                    person_details.save()

                    organisation_people.save()
                    self._save_m2m()
            else:
                self.save_m2m = self._save_m2m
        return person_details

    class Meta:
        model = PersonDetails
        fields = ['first_name', 'middle_name', 'last_name', 'position_email',
                  'contact_email', 'contact_phone', 'title', ]

        widgets = {
            "first_name": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "middle_name": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "last_name": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "contact_email": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "contact_phone": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "title": PersonTitlePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class OrganisationDocumentForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        org = kwargs.pop('organisation')
        super().__init__(*args, **kwargs)

        self.fields['type'].queryset = OrganisationDocumentType.objects.applicable_to_org(org)

    class Meta:
        model = OrganisationDocument
        fields = ['name', 'description', 'type', 'file', ]
        widgets = {
            "name": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "description": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            "type": OrganisationDocumentTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "file": widgets.FileInput(attrs={
                'class': 'form-control',
            }),
        }


class IpaDetailsForm(BSModalModelForm):

    class Meta:
        model = IpaDetails
        fields = ['iata_code', ]
        widgets = {
            "iata_code": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
        }


class IpaLocationsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].empty_label = 'Type Airport Name/ICAO/IATA'

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = IpaLocation
        fields = ['location', 'fuel', 'location_email', 'location_phone',]
        widgets = {
            "location": AirportPickWidget(attrs={
                'class': 'form-control'
            }),
            "fuel": FuelTypesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "location_email": widgets.EmailInput(attrs={
                'class': 'form-control'
            }),
            "location_phone": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
        }


class IpaLocationsBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)
        if self.organisation:
            self.queryset = IpaLocation.objects.filter(
                organisation=self.organisation).all()
        else:
            self.queryset = IpaLocation.objects.none()
        self.forms[0].empty_permitted = False
        for field in self.forms[0].fields:
            field_required_flag = self.forms[0].fields[field].required
            if field_required_flag == True:
                self.forms[0].fields[field].widget.attrs['required'] = 'required'

    def clean(self):
        locations = set()

        for form in self.forms:
            location = form.cleaned_data.get('location')

            if location:
                if location in locations:
                    form.add_error('location', 'Each airport/location has to be unique.')

                locations.add(location)

IpaLocationsFormSet = modelformset_factory(
    IpaLocation,
    extra=50,
    can_delete=True,
    form=IpaLocationsForm,
    formset=IpaLocationsBaseFormSet,
    fields=['location', 'fuel', 'location_email', 'location_phone']
)


class HandlerDetailsForm(forms.ModelForm):
    is_ipa = forms.BooleanField(
        label='Is an Into-Plane Agent?',
        required=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input d-block mt-2',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'organisation'):
            if hasattr(self.instance.organisation, 'ipa_details'):
                self.fields['is_ipa'].initial = True

    class Meta:
        model = HandlerDetails
        fields = ['airport', 'handler_type', 'is_ipa',
                  'ops_email', 'ops_phone', 'ops_frequency',
                  'contact_email', 'contact_phone',
                  'is_in_gat', 'is_in_cargo_centre', 'is_in_airport_terminal',
                  'handles_military', 'handles_airlines', 'handles_cargo', 'handles_ba_ga',
                  'has_pax_lounge', 'has_crew_room', 'has_vip_lounge', ]
        widgets = {
            "airport": AirportPickWidget(attrs={
                'class': 'form-control',
            }),
            "handler_type": HandlerTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "is_ipa": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "ops_email": widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            "ops_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "ops_frequency": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            "contact_email": widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            "contact_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "is_in_gat": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_in_cargo_centre": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "is_in_airport_terminal": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "handles_military": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "handles_airlines": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "handles_cargo": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "handles_ba_ga": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "has_pax_lounge": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "has_crew_room": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "has_vip_lounge": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
        }


class GroundHandlerFuelTypeForm(BSModalModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = IpaLocation
        fields = ['fuel', ]
        widgets = {
            "fuel": FuelTypesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class OilcoFuelTypesForm(BSModalModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = Organisation
        fields = ['oilco_fuel_types', ]
        widgets = {
            "oilco_fuel_types": FuelTypesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class OilcoDetailsForm(forms.ModelForm):

    class Meta:
        model = OilcoDetails
        fields = ['iata_code', ]
        widgets = {
            "iata_code": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
        }


class NasdlDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = NasdlDetails
        fields = ['type', 'latitude', 'longitude',
                  'what3words_code', 'use_address', 'comment_guidance', ]
        widgets = {
            "type": NasdTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "latitude": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            "longitude": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            "what3words_code": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '///lock.spout.area',
            }),
            "use_address": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "comment_guidance": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }

    def clean(self):
        # NASDL details can't be added to orgs of other types
        if self.organisation and self.organisation.details.type_id != 1002:
            self.add_error(None, "NASDL details cannot be added to organisations of other types")


class ServiceProviderLocationForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_location'].empty_label = 'Type Airport Name/ICAO/IATA'

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationServiceProviderLocation
        fields = ['delivery_location', 'ground_services', 'is_fbo', ]
        widgets = {
            "delivery_location": ServiceProviderLocationPickWidget(attrs={
                'class': 'form-control'
            }),
            "ground_services": GroundServicesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "is_fbo": widgets.CheckboxInput(attrs={
                'class': 'form-check-input mt-2',
            }),
        }


class ServiceProviderLocationBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)
        if self.organisation:
            self.queryset = OrganisationServiceProviderLocation.objects.filter(
                organisation=self.organisation).all()
        else:
            self.queryset = OrganisationServiceProviderLocation.objects.none()
        self.forms[0].empty_permitted = False
        for field in self.forms[0].fields:
            field_required_flag = self.forms[0].fields[field].required
            if field_required_flag == True:
                self.forms[0].fields[field].widget.attrs['required'] = 'required'


ServiceProviderLocationFormSet = modelformset_factory(
    OrganisationServiceProviderLocation,
    extra=50,
    can_delete=True,
    form=ServiceProviderLocationForm,
    formset=ServiceProviderLocationBaseFormSet,
    fields=['delivery_location', 'ground_services', 'is_fbo', ]
)


class TripSupportCompanyClientForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].empty_label = 'Pick Aircraft Operator Organisation'

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = TripSupportClient
        fields = ['client', ]
        widgets = {
            "client": OrganisationPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class TripSupportCompanyClientBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)
        if self.organisation:
            self.queryset = TripSupportClient.objects.filter(
                organisation=self.organisation).all()
        else:
            self.queryset = TripSupportClient.objects.none()


TripSupportCompanyClientFormSet = modelformset_factory(
    TripSupportClient,
    extra=50,
    can_delete=True,
    form=TripSupportCompanyClientForm,
    formset=TripSupportCompanyClientBaseFormSet,
    fields=['client', ]
)


class OrganisationLogoMottoForm(forms.ModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationLogoMotto
        fields = ['logo', 'motto', 'cascade_to_departments', ]
        widgets = {
            "logo": widgets.FileInput(attrs={
                'class': 'form-control',
            }),
            "motto": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "cascade_to_departments": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block mt-2',
            }),
        }


class OrganisationLogoMottoModalForm(BSModalModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationLogoMotto
        fields = ['logo', 'motto', 'cascade_to_departments', ]
        widgets = {
            "logo": widgets.FileInput(attrs={
                'class': 'form-control',
            }),
            "motto": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "cascade_to_departments": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class OperatorPreferredGroundHandlerForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Remove existing locations from the list
        existing_locations_pks = self.instance.organisation.operator_preferred_handlers.values_list(
            'location_id', flat=True)

        qs = Organisation.objects.airport().exclude(
            pk__in=existing_locations_pks,
        )
        self.fields['location'].queryset = qs

        # Remove existing handlers from the list
        existing_handlers_pks = self.instance.organisation.operator_preferred_handlers.values_list(
            'ground_handler_id', flat=True)

        qs = Organisation.objects.handling_agent().exclude(
            pk__in=existing_handlers_pks,
        )
        self.fields['ground_handler'].queryset = qs

    class Meta:
        model = OperatorPreferredGroundHandler
        fields = ['location', 'ground_handler', ]
        widgets = {
            "location": AirportPickWidget(attrs={
                'class': 'form-control',
            }),
            "ground_handler": OperatorPreferredHandlerDependentPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class GroundHandlerOpsPortalSettingsForm(forms.ModelForm, PopRequestMixin):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        organisation_logo_motto = getattr(self.instance.organisation, 'logo_motto', None)
        if not organisation_logo_motto:
            self.fields['spf_use_aml_logo'].disabled = True

        if not self.request.user.has_perm('core.p_contacts_update'):
            for field in self.fields:
                self.fields[field].disabled = True

    class Meta:
        model = OrganisationOpsDetails
        fields = ['receives_parking_chase_email', 'spf_use_aml_logo', ]
        widgets = {
            "receives_parking_chase_email": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            "spf_use_aml_logo": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class PaymentMethodForm(BSModalModelForm):

    currency = OrganisationAcceptedPaymentMethod.currency.field.formfield(
        widget=CurrencyPickWidget(
            attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['name'].initial = self.instance.name
            self.fields['currency'].initial = self.instance.accepted_payment_method.currency
            self.fields['is_card'].initial = self.instance.is_card
            self.fields['is_cash'].initial = self.instance.is_cash
            self.fields['is_on_account'].initial = self.instance.is_on_account
            self.fields['is_credit'].initial = self.instance.is_credit

    class Meta:
        model = OrganisationPaymentMethod
        modal_id = 'payment-modal'
        fields = ['name', 'currency', 'is_cash', 'is_card', 'is_credit', 'is_on_account']
        widgets = {
            "name": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "currency": widgets.Select(attrs={
                'class': 'form-control'
            }),
            "is_cash": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            "is_card": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            "is_credit": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            "is_on_account": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def save(self, commit=True):
        payment_method = super().save(commit=False)
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():
                    currency = self.cleaned_data['currency']
                    if self.instance.pk is None:
                        payment_method.save()
                        accepted_payment_method = OrganisationAcceptedPaymentMethod()
                        accepted_payment_method.organisation = Organisation.objects.get(id = self.organisation)
                        accepted_payment_method.payment_method = payment_method
                        accepted_payment_method.currency = currency
                        accepted_payment_method.save()
                    else:
                        payment_method.save()
                        accepted_payment_method = OrganisationAcceptedPaymentMethod.objects.get(
                            payment_method = self.instance.id)
                        accepted_payment_method.currency = currency
                        accepted_payment_method.save()

        return payment_method


class OrganisationContactDetailsForm(forms.ModelForm):
    comms_settings_supplier = forms.MultipleChoiceField(
        required=False, label="Supplier Communications - Include In:",
        choices=[(k, v[1]) for k, v in OrganisationContactDetails.COMMS_SUPPLIER_CHOICES.items()],
        widget=s2forms.Select2MultipleWidget(attrs={
            'class': 'form-control',
            'data-placeholder': 'Use Cases for Supplier (if applicable)',
        }),
    )
    comms_settings_client = forms.MultipleChoiceField(
        required=False, label="Client Communications - Include In:",
        choices=[(k, v[1]) for k, v in OrganisationContactDetails.COMMS_CLIENT_CHOICES.items()],
        widget=s2forms.Select2MultipleWidget(
            attrs={
                'class': 'form-control',
                'data-placeholder': 'Use Cases for Client (if applicable)',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)

        # Limit selectable people to those associated with org
        self.fields['organisations_people'].queryset = self.organisation.organisation_people.all()

        self.fields['comms_settings_client'].initial = self.instance.comms_settings_client
        self.fields['comms_settings_supplier'].initial = self.instance.comms_settings_supplier

    class Meta:
        model = OrganisationContactDetails
        fields = ['description', 'organisations_people', 'locations', 'phone_number', 'phone_number_use_for_whatsapp',
                  'phone_number_use_for_telegram', 'email_address', 'address_to', 'address_cc', 'address_bcc',
                  'comms_settings_supplier', 'comms_settings_client' ]
        widgets = {
            "description": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a Description',
            }),
            "organisations_people": OrganisationRolePickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Person / Role',
                'data-minimum-input-length': '0',
            }),
            "locations": AirportsPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Airports',
            }),
            "phone_number": widgets.TextInput(attrs={
                'class': 'form-control form-field-w-100',
                'placeholder': 'Enter a Phone Number',
            }),
            "email_address": widgets.TextInput(attrs={
                'class': 'form-control form-field-w-100',
                'placeholder': 'Enter an Email Address',
            }),
            'phone_number_use_for_whatsapp': widgets.CheckboxInput(attrs={
                'class': 'form-check-input ms-2',
            }),
            'phone_number_use_for_telegram': widgets.CheckboxInput(attrs={
                'class': 'form-check-input ms-2',
            }),
            'address_to': widgets.CheckboxInput(attrs={
                'class': 'form-check-input ms-2',
            }),
            'address_cc': widgets.CheckboxInput(attrs={
                'class': 'form-check-input ms-2',
            }),
            'address_bcc': widgets.CheckboxInput(attrs={
                'class': 'form-check-input ms-2',
            }),
        }

    def clean_description(self):
        """
        Remove any multiple spaces from description, to prevent issues with
        the tagify field additional_emails in PricingUpdateRequestSend form
        """
        val = self.cleaned_data['description']

        return re.sub(r'\s+', ' ', val)

    def clean(self):
        data = self.cleaned_data
        # Email is mandatory if no person was selected
        if not data.get('email_address') and not data.get('organisations_people'):
            if not self.errors.get('email_address'):
                self.add_error('email_address', 'Email address is required when no person specified')

        # If email provided, one of the fields must be selected
        if data.get('email_address'):
            if not any([data.get('address_to'), data.get('address_cc'), data.get('address_bcc')]):
                self.add_error('email_address', 'Select the email field to use for this address')

        # Email + person combinations must be unique for the org
        if data.get('email_address') and data.get('organisations_people'):
            existing_people_emails = self.organisation.organisation_contact_details.values_list(
                'organisations_people', 'email_address').exclude(pk=self.instance.pk)

            if (data.get('organisations_people').pk, data.get('email_address')) in existing_people_emails:
                self.add_error('email_address', 'A record associating this email address with this person'
                                                ' already exists')
        elif data.get('email_address'):
            existing_emails = self.organisation.organisation_contact_details.values_list(
                'email_address', flat=True).exclude(pk=self.instance.pk)

            if data.get('email_address') in existing_emails:
                self.add_error('email_address', 'A record for this email address already exists')

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid


class OrganisationContactDetailsEditForm(PopRequestMixin, CreateUpdateAjaxMixin, OrganisationContactDetailsForm):
    '''
    This class is to use the (mostly) same details form as on create page, but in a modal.
    Minor differences in checkbox widget details for display purposes.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['phone_number_use_for_whatsapp'].widget = widgets.CheckboxInput(attrs={
            'class': 'form-check-input checkbox-force-inline me-2',
        })
        self.fields['phone_number_use_for_telegram'].widget = widgets.CheckboxInput(attrs={
            'class': 'form-check-input checkbox-force-inline ms-1 me-2',
        })
        self.fields['address_to'].widget = widgets.CheckboxInput(attrs={
            'class': 'form-check-input checkbox-force-inline me-2',
        })
        self.fields['address_cc'].widget = widgets.CheckboxInput(attrs={
            'class': 'form-check-input checkbox-force-inline ms-1 me-2',
        })
        self.fields['address_bcc'].widget = widgets.CheckboxInput(attrs={
            'class': 'form-check-input checkbox-force-inline ms-1 me-2',
        })


class OrganisationContactDetailsBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)

        self.queryset = OrganisationContactDetails.objects.none()

        # Make required first form in formset
        self.forms[0].empty_permitted = False
        for field in self.forms[0].fields:
            field_required_flag = self.forms[0].fields[field].required
            if field_required_flag == True:
                self.forms[0].fields[field].widget.attrs['required'] = 'required'

    def clean(self):
        # Here we check all the pairs of submitted people / emails (need to be unique)
        # We check against existing records in the form's clean method
        new_people_emails = [(f.cleaned_data.get('organisations_people'), f.cleaned_data.get('email_address'))
                             for f in self.forms
                             if f.cleaned_data.get('organisations_people') and f.cleaned_data.get('email_address')]
        duplicate_people_emails = [item for item, count in Counter(new_people_emails).items() if count > 1]

        for form in self.forms:
            person_email = (form.cleaned_data.get('organisations_people'), form.cleaned_data.get('email_address'))

            if person_email in duplicate_people_emails:
                form.add_error('email_address', 'This combination of person and email address is duplicated')


OrganisationContactDetailsFormSet = modelformset_factory(
    OrganisationContactDetails,
    extra=50,
    can_delete=True,
    form=OrganisationContactDetailsForm,
    formset=OrganisationContactDetailsBaseFormSet,
)


class HandlerSpfServiceForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.handler = kwargs.pop('handler', None)
        super().__init__(*args, **kwargs)
        self.instance.handler = self.handler
        self.fields['dla_service'].queryset = DlaService.objects.get_for_handler_auto_select(self.handler)

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = HandlerSpfService
        fields = [
            'dla_service',
            'applies_after_minutes',
            'applies_if_pax_onboard',
            'applies_if_cargo_onboard',
        ]
        widgets = {
            'dla_service': DlaServicePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            'applies_after_minutes': widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            'applies_if_pax_onboard': widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'applies_if_cargo_onboard': widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class HandlerSpfServiceBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.handler = kwargs.pop('handler', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.queryset = HandlerSpfService.objects.none()

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['handler'] = self.handler
        return kwargs


HandlerSpfServiceFormSet = modelformset_factory(
    HandlerSpfService,
    extra=30,
    can_delete=False,
    form=HandlerSpfServiceForm,
    formset=HandlerSpfServiceBaseFormSet,
    fields=[
        'dla_service',
        'applies_after_minutes',
        'applies_if_pax_onboard',
        'applies_if_cargo_onboard',
    ]
)


class HandlerCancellationBandForm(forms.ModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = HandlerCancellationBand
        fields = [
            'notification_band_start_hours',
            'notification_band_end_hours',
        ]
        widgets = {
            'notification_band_start_hours': widgets.NumberInput(attrs={
                'maxlength': 2,
                'class': 'form-control',
            }),
            'notification_band_end_hours': widgets.NumberInput(attrs={
                'maxlength': 4,
                'class': 'form-control',
            }),
        }


class HandlerCancellationBandTermForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.handler_cancellation_band = kwargs.pop('handler_cancellation_band', None)
        super().__init__(*args, **kwargs)
        self.fields['penalty_specific_service'].queryset = HandlingService.objects.dod_all(
            organisation=self.handler_cancellation_band.handler,
        )

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = HandlerCancellationBandTerm
        fields = [
            'penalty_specific_service',
            'penalty_percentage',
            'penalty_amount',
            'penalty_amount_currency',
        ]
        widgets = {
            'penalty_specific_service': HandlingServicePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            'penalty_percentage': widgets.NumberInput(attrs={
                'maxlength': 3,
                'class': 'form-control',
            }),
            'penalty_amount': widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            'penalty_amount_currency': CurrencyPickWidget(attrs={
                'class': 'form-control',
            }),
        }


class HandlerCancellationBandTermBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.handler_cancellation_band = kwargs.pop('handler_cancellation_band')
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.handler_cancellation_band.pk:
            self.queryset = self.handler_cancellation_band.cancellation_terms.all()
        else:
            self.queryset = HandlerCancellationBandTerm.objects.none()

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['handler_cancellation_band'] = self.handler_cancellation_band
        return kwargs

    def clean(self):
        forms_to_delete = self.deleted_forms
        valid_forms = [
            form
            for form in self.forms
            if form.is_valid() and form not in forms_to_delete
        ]

        # Get id's for every instance selected to delete to exclude it in duplicate check
        instance_pks_to_delete = [form.instance.pk for form in forms_to_delete]
        instances_to_save = []

        for form in valid_forms:
            if form.instance.pk not in instance_pks_to_delete and form.instance.get_penalty_display():
                instances_to_save.append(form.instance.pk)

        cleaned_data = super().clean()

        if not instances_to_save or not valid_forms:
            raise forms.ValidationError('Please specify at least one cancellation term to save')

        return cleaned_data
