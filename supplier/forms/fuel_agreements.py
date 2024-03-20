from datetime import date, datetime

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import widgets
from django.views.generic.edit import ModelFormMixin
from django_select2 import forms as s2forms
from bootstrap_modal_forms.forms import BSModalModelForm

from core.form_widgets import CurrencyPickWidget
from organisation.form_widgets import OrganisationWithTypePickWidget
from organisation.models import Organisation, OrganisationDocument
from pricing.form_widgets import AmlGroupCompanyPickWidget
from pricing.utils import agreement_extension_check_overlap
from pricing.utils.fuel_pricing_market import normalize_fraction
from supplier.models import FuelAgreement


class FuelAgreementDetailsForm(ModelFormMixin, BSModalModelForm):
    '''
    Form for Fuel Agreement management
    '''
    payment_terms_unit_count = forms.IntegerField(
        label='Payment Terms',
        required=False,
        widget=widgets.NumberInput(attrs={
            'class': 'form-control extend-label form-field-w-60',
            'min': 0,
            'step': 1,
        })
    )
    payment_terms_time_unit = forms.ChoiceField(
        label='Time Unit',
        required=False,
        choices=[('D', 'Days'), ('M', 'Months')],
        widget=s2forms.Select2Widget(
            attrs={
                'class': 'form-control no-label form-field-w-40',
                'data-allow-clear': 'false',
            }
        ),
    )
    source_doc_name = OrganisationDocument.name.field.formfield(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        }),
    )
    source_doc_file = OrganisationDocument.file.field.formfield(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control mb-1',
        }),
    )
    source_doc_description = OrganisationDocument.description.field.formfield(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        }),
    )
    end_date = forms.DateField(
        widget=widgets.DateInput(attrs={
            'class': 'form-control',
            'data-datepicker': '',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.mode = kwargs.pop('mode', None)
        self.old_agreement = kwargs.pop('old_agreement', None)

        super().__init__(*args, **kwargs)

        self.fields['supplier_agreement_reference'].label = 'Supplier Reference'
        self.fields['end_date'].required = False
        self.fields['source_doc_name'].required = False
        self.fields['source_doc_file'].required = False

        # Disable fields that are updated with special functionalities on edit
        # (extend, void, supersede). Also supplier, as is done for market pricing
        if self.instance.pk is not None:
            self.fields['supplier'].disabled = True
            self.fields['start_date'].disabled = True
            self.fields['end_date'].disabled = True
            self.fields['valid_ufn'].disabled = True
            self.initial['deposit_amount'] = normalize_fraction(self.initial['deposit_amount'])

        # When superseding, fix the supplier and prepopulate other fields with defaults
        if self.mode == 'supersede' and self.old_agreement:
            self.fields['supplier'].disabled = True
            self.fields['supplier'].initial = self.old_agreement.supplier
            self.initial['deposit_required'] = self.old_agreement.deposit_required
            self.initial['deposit_amount'] = normalize_fraction(self.old_agreement.deposit_amount)
            self.initial['deposit_currency'] = self.old_agreement.deposit_currency

            # Add supplier org if not included in limit_choices_to
            self.fields['supplier'].queryset = Organisation.objects.filter(
                Q(pk__in=self.fields['supplier'].queryset) | Q(pk=self.fields['supplier'].initial.pk))

            self.fields['aml_group_company'].initial = self.old_agreement.aml_group_company
            self.fields['aml_is_agent'].initial = self.old_agreement.aml_is_agent

            if self.old_agreement.is_prepayment:
                self.fields['is_prepayment'].initial = True
            elif self.old_agreement.payment_terms_days:
                self.fields['payment_terms_unit_count'].initial = self.old_agreement.payment_terms_days
                self.fields['payment_terms_time_unit'].initial = 'D'
            elif self.old_agreement.payment_terms_months:
                self.fields['payment_terms_unit_count'].initial = self.old_agreement.payment_terms_months
                self.fields['payment_terms_time_unit'].initial = 'M'

            self.fields['priority'].initial = self.old_agreement.priority

        if self.instance.is_prepayment or self.mode == 'create':
            self.fields['is_prepayment'].initial = True
        elif self.instance.payment_terms_days:
            self.fields['payment_terms_unit_count'].initial = self.instance.payment_terms_days
            self.fields['payment_terms_time_unit'].initial = 'D'
        elif self.instance.payment_terms_months:
            self.fields['payment_terms_unit_count'].initial = self.instance.payment_terms_months
            self.fields['payment_terms_time_unit'].initial = 'M'

        if self.instance.document:
            self.fields['source_doc_name'].initial = self.instance.document.name
            self.fields['source_doc_file'].initial = self.instance.document.file
            self.fields['source_doc_description'].initial = self.instance.document.description

    class Meta:
        model = FuelAgreement
        fields = ('supplier', 'supplier_agreement_reference', 'aml_reference', 'aml_reference_legacy',
                  'aml_group_company', 'aml_is_agent', 'start_date', 'end_date', 'valid_ufn', 'is_prepayment',
                  'priority', 'deposit_required', 'deposit_amount', 'deposit_currency')

        widgets = {
            "supplier": OrganisationWithTypePickWidget(attrs={
                'class': 'form-control',
            }),
            "supplier_agreement_reference": widgets.TextInput(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "aml_reference": widgets.TextInput(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "aml_reference_legacy": widgets.TextInput(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "aml_group_company": AmlGroupCompanyPickWidget(attrs={
                'class': 'form-control',
            }),
            "aml_is_agent": widgets.CheckboxInput(attrs={
                'class': 'd-block',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }),
            "start_date": widgets.DateInput(attrs={
                'class': 'form-control',
                'data-datepicker': '',
            }),
            "valid_ufn": widgets.CheckboxInput(attrs={
                'class': 'd-block',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }),
            "is_prepayment": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block mt-2',
            }),
            "priority": s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            "deposit_required": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block mt-2',
            }),
            "deposit_amount": widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
                'placeholder': 'Deposit Amount',
                'step': 0.01,
            }),
            "deposit_currency": CurrencyPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Currency',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_start_date = cleaned_data['start_date']

        # If not valid UFN, new date is required
        if not cleaned_data['valid_ufn']:
            new_end_date = cleaned_data['end_date']

            if not new_end_date:
                self.add_error('end_date',
                               ValidationError("A new date must be specified if 'Valid UFN' is not selected"))
            elif new_start_date and new_end_date <= new_start_date:
                self.add_error('end_date', ValidationError(
                    f"The end date has to be after the start date ({new_start_date})"
                ))
            elif self.mode == 'supersede' and new_start_date and new_end_date <= date.today():
                self.add_error('end_date', ValidationError(
                    f"The end date of new agreement has to be in the future"
                ))

        # Additional validation when superseding
        if self.mode == 'supersede':
            if new_start_date <= self.old_agreement.start_date:
                self.add_error('start_date', ValidationError(
                    f"The start date of new agreement has to be after the start date of superseded agreement "
                    f"({self.old_agreement.start_date})"
                ))

        # If source document file or name are provided, both become mandatory
        has_file = self.request.FILES.get('source_doc_file', None) or getattr(self.instance.document, 'file', None)

        if cleaned_data['source_doc_name'] and not has_file:
            self.add_error('source_doc_file', ValidationError("File upload is mandatory when name is provided"))
        if not cleaned_data['source_doc_name'] and has_file:
            self.add_error('source_doc_name', ValidationError("Name is mandatory when a file is provided"))

        # Payment conditions need to be specified
        if not cleaned_data['is_prepayment']:
            if not cleaned_data['payment_terms_unit_count']:
                self.add_error('payment_terms_unit_count',
                               ValidationError("This field is required if 'Is Prepayment?' is not selected"))
            if not cleaned_data['payment_terms_time_unit']:
                self.add_error('payment_terms_time_unit',
                               ValidationError("This field is required if 'Is Prepayment?' is not selected"))

        # Deposit details must be specified if deposit required
        if cleaned_data.get('deposit_required'):
            if not cleaned_data.get('deposit_amount') and not self.has_error('deposit_amount'):
                self.add_error('deposit_amount',
                               ValidationError("This field is required if 'Deposit Required?' is selected"))
            if not cleaned_data.get('deposit_currency') and not self.has_error('deposit_currency'):
                self.add_error('deposit_currency',
                               ValidationError("This field is required if 'Deposit Required?' is selected"))

        return cleaned_data


class FuelAgreementExtendForm(BSModalModelForm):
    """
    Form to extend a fuel agreement
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['end_date'].initial = self.instance.end_date

    def clean(self):
        '''
        If valid_ufn is false, ensure the date is in the future
        and later than the current end date. Also check for overlaps.
        '''
        cleaned_data = super().clean()
        fuel_agreement = self.instance

        # If not valid UFN, new date is required
        new_end_date = cleaned_data['end_date']

        if not cleaned_data['valid_ufn']:
            if not new_end_date:
                self.add_error('end_date', ValidationError("A new date must be specified if 'Valid UFN' is not selected"))
            elif new_end_date <= date.today():
                self.add_error('end_date', ValidationError("Please enter a future date"))
            elif fuel_agreement.end_date and new_end_date <= fuel_agreement.end_date.date():
                self.add_error('end_date', ValidationError(f"The extension date has to be after the current end date"
                                                           f" ({fuel_agreement.end_date.strftime('%Y-%m-%d')})"))

        overlap_msg = agreement_extension_check_overlap(fuel_agreement, new_end_date)

        if overlap_msg:
            self.add_error(None, ValidationError(overlap_msg))

        return cleaned_data

    def is_valid(self):
        for field in self.errors:
            if field == '__all__':
                continue

            if isinstance(self.fields[field].widget, widgets.CheckboxInput):
                self.fields[field].widget.attrs['class'] = 'form-check-input is-invalid'
            else:
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'

        return super().is_valid()

    end_date = forms.DateField(
        required=False,
        label="New End Date",
        widget=widgets.DateInput(
            attrs={
                'class': 'form-control',
                'data-datepicker': '',
            }
        ),
    )
    valid_ufn = forms.BooleanField(
        required=False,
        label="Valid UFN",
        widget=widgets.CheckboxInput(
            attrs={
                'class': 'form-check-input',
            }
        ),
    )

    class Meta:
        model = FuelAgreement
        modal_id = 'extend-modal'
        fields = ['end_date', 'valid_ufn']


class FuelAgreementVoidForm(BSModalModelForm):
    """
    Form to void a fuel agreement
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['end_date'] = self.instance.end_date or datetime.today().date()

    def clean(self):
        '''
        Ensure the date is not in the past and before the current end date
        '''
        cleaned_data = super().clean()
        fuel_agreement = self.instance
        new_end_date = cleaned_data['end_date']
        void_immediately = cleaned_data['void_immediately']

        if not void_immediately:
            if not new_end_date:
                self.add_error('end_date', ValidationError("A new date must be specified."))
            elif new_end_date < date.today():
                self.add_error('end_date', ValidationError("The new end date cannot be in the past."))
            elif fuel_agreement.end_date and new_end_date >= fuel_agreement.end_date.date():
                self.add_error('end_date', ValidationError(
                    f"The new end date has to be before the current end date ({fuel_agreement.end_date.date()})"
                ))
            elif not fuel_agreement.has_started and new_end_date < fuel_agreement.start_date:
                self.add_error('end_date', ValidationError("The new end date cannot precede the start date."))
        else:
            if fuel_agreement.start_date > date.today():
                self.add_error('void_immediately',
                               ValidationError("Only an already started agreement can be voided immediately."))

        return cleaned_data

    def is_valid(self):
        for field in self.errors:
            if isinstance(self.fields[field].widget, widgets.CheckboxInput):
                self.fields[field].widget.attrs['class'] = 'form-check-input is-invalid'
            else:
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'

        return super().is_valid()

    end_date = forms.DateField(
        required=False,
        label="New End Date",
        widget=widgets.DateInput(
            format="%Y-%m-%d",
            attrs={
                'class': 'form-control',
                'data-datepicker': '',
            }
        ),
    )
    void_immediately = forms.BooleanField(
        label='Void Immediately',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )

    class Meta:
        model = FuelAgreement
        modal_id = 'void-modal'
        fields = ['end_date', ]

