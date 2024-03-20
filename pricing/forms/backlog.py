from django import forms
from django.db.models import Q
from django_select2 import forms as s2forms
from tagify.fields import TagField

from core.forms import ConfirmationForm
from core.form_widgets import CustomTagInput
from organisation.form_widgets import AirportsPickWidget
from organisation.models import Organisation


class PricingUpdateRequestSend(ConfirmationForm):
    locations = forms.ModelMultipleChoiceField(
        label='Locations',
        required=True,
        queryset=Organisation.objects.all(),
        widget=AirportsPickWidget(attrs={
            'class': 'form-control',
            'data-placeholder': 'Select Locations',
            'data-minimum-input-length': 0,
        }),
    )
    send_to_people = forms.MultipleChoiceField(
        label='Recipients',
        required=False,
        help_text='Select people who will receive copy of the handling request',
        widget=s2forms.Select2MultipleWidget(attrs={
            'class': 'form-control',
            'data-minimum-input-length': 0,
        }),
    )
    additional_emails = TagField(
        label='Additional Emails to Copy In',
        required=False,
        suggestions_chars=0,
        delimiters='  ',
        pattern='^(TO:|CC:|BCC:)?[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\s?(\(.*\))?$',
        help_text='Emails can be added as'
                  ' <samp class="nowrap">FIELD:email@address.com (description)</samp>,'
                  ' and will be saved in organisation contact details for future use.<br>'
                  'Field and description are optional, CC will be used as default field.<br>'
                  'Use TAB or double space to separate entries.',
        widget=CustomTagInput(attrs={
            'class': 'form-control',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.supplier = kwargs.pop('supplier')
        self.handler_email_addresses = kwargs.pop('handler_email_addresses')
        self.doc_type = kwargs.pop('doc_type')
        self.doc_instance = kwargs.pop('doc_instance')
        super().__init__(*args, **kwargs)

        # Populate locations query based on document's pricing
        if self.doc_type == 'Agreement':
            self.fields['locations'].widget.queryset = Organisation.objects\
                .filter(pk__in=self.doc_instance.all_pricing_location_pks)
        else:
            locations_with_pricing_pks = self.doc_instance.pld_at_location.with_status()\
                .filter(~Q(location_status='No Pricing')).values_list('location', flat=True)
            self.fields['locations'].widget.queryset = Organisation.objects\
                .filter(pk__in=locations_with_pricing_pks)

        self.fields['locations'].initial = list(self.fields['locations'].widget.queryset.values_list('pk', flat=True))

        # Populate people selection field
        self.fields['send_to_people'].choices = self.get_send_to_people_choices()
        self.fields['send_to_people'].initial = list(self.supplier.organisation_contact_details.filter(
            supplier_include_for_fuel_pricing_updates=True,
            organisations_people__isnull=False
        ).values_list('pk', flat=True))

        # Populate additional emails field
        all_additional_emails = self.supplier.organisation_contact_details.filter(
            organisations_people__isnull=True)
        preselected_emails = self.supplier.organisation_contact_details.filter(
            supplier_include_for_fuel_pricing_updates=True,
            organisations_people__isnull=True)

        all_additional_emails = sorted(sorted(all_additional_emails, key=lambda x: x.email_address),
            key=lambda x: (x.address_to, x.address_cc, x.address_bcc), reverse=True)
        preselected_emails = sorted(sorted(preselected_emails, key=lambda x: x.email_address),
            key=lambda x: (x.address_to, x.address_cc, x.address_bcc), reverse=True)

        self.fields['additional_emails'].widget.tag_args['whitelist'] = \
            [e.repr_for_additional_emails_list for e in all_additional_emails]

        self.fields['additional_emails'].initial = \
            [e.repr_for_additional_emails_list for e in preselected_emails]

    def clean(self):
        data = self.cleaned_data

        if not data.get('send_to_people') and (not data.get('additional_emails') or data['additional_emails'] == ['']):
            self.add_error('send_to_people', 'Please specify at least one recipient for the request')
            self.add_error('additional_emails', 'Please specify at least one recipient for the request')

    def get_send_to_people_choices(self):
        positions = self.supplier.organisation_people.all()
        choices = []

        for pos in positions:
            contact_details = pos.organisation_contact_details.filter(email_address__isnull=False)

            if contact_details.exists():
                choices.extend([(cd.pk, cd.repr_for_recipients_list) for cd in contact_details])
            elif pos.contact_email:
                choices.append((f'new_from_pos_{pos.pk}', pos.repr_for_recipients_list))

        return sorted(sorted(sorted(choices, key=lambda x: (x[1].split('<br>')[1].split('</span>')[1])),
                      key=lambda x: (x[1].split('<br>')[1].split('</span>')[0]), reverse=True),
                      key=lambda x: (x[1].split('<br>')[0]))
