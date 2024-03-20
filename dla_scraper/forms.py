from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.forms import widgets
from django.forms.models import ModelChoiceField
from django.urls import reverse_lazy
from django_select2.forms import ModelSelect2Widget
from dla_scraper.models import *
from organisation.form_widgets import OrganisationPickWidget
from organisation.form_widgets import OrganisationTypePickWidget
from organisation.models import Organisation, OrganisationType


class DLAScraperForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DLAReconcileNameForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_required_attribute = False;
        self.fields['supplier'].widget.attrs['id'] = 'supplier_id_' + str(self.instance.id)
        self.fields['supplier'].widget.attrs['name'] = 'supplier_' + str(self.instance.id)

    id = forms.IntegerField(
        label='ID:',
        required=True,
        widget=widgets.TextInput(
            attrs={
                'readonly': True,
            }
        )
    )

    name = forms.CharField(
        label='Name:',
        required=False,
        widget=widgets.TextInput(
            attrs={
                'readonly': True,
            }
        )
    )

    supplier = forms.ModelChoiceField(
        queryset=Organisation.objects.all(),
        label='Organisation:',
        required=True,
        widget=OrganisationPickWidget(
            attrs={
                'class': 'form-control',
            }
        )
    )

    class Meta:
        model = DLASupplierName
        fields = ['id', 'name', 'supplier']


class DLASelectOrgTypeForm(BSModalForm):
    """
    Form for selection of organisation type to be created
    """

    def __init__(self, *args, **kwargs):
        self.dla_name_id = kwargs.pop('dla_name_id')

        super().__init__(*args, **kwargs)
        self.fields['dla_name_id'].initial = self.dla_name_id
        self.fields['type'].empty_label = 'Please select organisation type'

        choices = [(None, 'Please select organisation type')]
        choices.extend(map(lambda x: (x.id, 'Ground Handler' if x.name == 'Handling Agent' else x.name), list(OrganisationType.objects.filter(
            pk__in=[1, 2, 3, 4, 5, ]
        ))))

        self.fields['type'].choices = choices

    dla_name_id = forms.IntegerField(
        label='Organisation Type:',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }
        )
    )

    type = forms.ChoiceField(
        label='Organisation Type:',
        required=True,
        widget=forms.Select(
            attrs={
                'class': 'form-control',
            }
        )
    )

    class Meta:
        model = OrganisationType
        fields = ['dla_name_id', 'type', ]


class DLAPendingOrganisationUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    id = forms.IntegerField(
        label='ID:',
        required=True,
        widget=widgets.TextInput(
            attrs={
                'readonly': True,
            }
        )
    )

    class Meta:
        model = DLAScraperPendingOrganisationUpdate
        fields = ['id']
