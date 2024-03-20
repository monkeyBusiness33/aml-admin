from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalFormView, BSModalUpdateView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import TemplateView
from ajax_datatable.views import AjaxDatatableView
from django.shortcuts import get_object_or_404
from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_clipped_value
from organisation.models import Organisation
from user.models import Person
from user.mixins import AdminPermissionsMixin
from .models import *
from .forms import *


class OrganisationPeopleActivitiesAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationPeopleActivity
    search_values_separator = '+'
    initial_order = [["is_pinned", "desc"], ["datetime", "desc"], ]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        entity_slug = self.kwargs.get('entity_slug')
        entity_pk = self.kwargs.get('entity_pk')

        if entity_slug == 'organisation':
            qs = OrganisationPeopleActivity.objects.filter(
                organisation_id=entity_pk)
        elif entity_slug == 'person':
            qs = OrganisationPeopleActivity.objects.filter(
                person_id=entity_pk)
        else:
            qs = OrganisationPeopleActivity.objects.none()

        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'created_by', 'title': 'Recorded By', 'foreign_field': 'created_by__details__abbreviated_name',
            'visible': True, },
        {'name': 'datetime', 'visible': True, 'choices': True, 'searchable': False, },
        {'name': 'crm_activity', 'title': 'Activity Type', 'foreign_field': 'crm_activity__name',
            'visible': True, },
        {'name': 'opportunity_order', 'title': 'Opportunity / Order', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False,},
        {'name': 'description', 'visible': True, 'searchable': False, 'width': '450px'},
        {'name': 'attachments_icons', 'title': 'Attachments', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False,},
        {'name': 'is_pinned', 'visible': True, 'searchable': False, },
    ]

    def customize_row(self, row, obj):
        row['datetime'] = obj.datetime.strftime("%Y-%m-%d %H:%M")
        row['opportunity_order'] = '--'
        row['description'] = get_datatable_clipped_value(text=obj.description, max_length=150)

        if obj.is_pinned:
            pinned_class = 'text-success fa-thumbtack'
        else:
            pinned_class = 'text-gray-300 fa-thumbtack'

        attachment_list = []
        for attachment in obj.attachments.all():
            btn = get_datatable_actions_button(button_text='',
                                               button_url=attachment.file.url,
                                               button_class='fa-file-download',
                                               button_active=self.request.user.has_perm('user.change_person'),
                                               button_popup=attachment.description,
                                               button_modal=False,
                                               modal_validation=False)

            attachment_list.append(btn)
        row['attachments_icons'] = ''.join(map(str, attachment_list))

        pin_btn = get_datatable_actions_button(button_text='',
                                               button_url=reverse_lazy(
                                                   'admin:crm_activity_pin', kwargs={'pk': obj.pk}),
                                               button_class=pinned_class,
                                               button_active=self.request.user.has_perm(
                                                   'crm.change_organisationpeopleactivity'),
                                               button_modal=True,
                                               modal_validation=False)

        row['is_pinned'] = pin_btn
        return


class OrganisationPeopleActivityCreateView(AdminPermissionsMixin, TemplateView):
    template_name = 'organisation_people_activity_modal.html'
    permission_required = ['core.p_contacts_update']

    def get(self, request, *args, **kwargs):

        entity_slug = self.kwargs.get('entity_slug')
        entity_pk = self.kwargs.get('entity_pk')
        activity_instance = OrganisationPeopleActivity(created_by=request.user.person)

        if entity_slug == 'organisation':
            organisation = get_object_or_404(Organisation, pk=entity_pk)
            activity_instance.organisation = organisation
        elif entity_slug == 'person':
            person = get_object_or_404(Person, pk=entity_pk)
            activity_instance.person = person

        return self.render_to_response({

            'organisation_people_activity_form': OrganisationPeopleActivityForm(
                instance=activity_instance,
                prefix='organisation_people_activity_form_pre'),

            'activity_attachment_formset': OrganisationPeopleActivityAttachmentFormSet(
                activity=activity_instance,
                prefix='activity_attachment_formset_pre'),
        })
    def post(self, request, *args, **kwargs):
        entity_slug = self.kwargs.get('entity_slug')
        entity_pk = self.kwargs.get('entity_pk')
        activity_instance = OrganisationPeopleActivity(created_by=request.user.person)

        if entity_slug == 'organisation':
            organisation = get_object_or_404(Organisation, pk=entity_pk)
            activity_instance.organisation = organisation
        elif entity_slug == 'person':
            person = get_object_or_404(Person, pk=entity_pk)
            activity_instance.person = person

        organisation_people_activity_form = OrganisationPeopleActivityForm(request.POST or None,
                                                                           instance=activity_instance,
                                                                           prefix='organisation_people_activity_form_pre')

        activity_attachment_formset = OrganisationPeopleActivityAttachmentFormSet(request.POST or None, request.FILES or None,
                                                                                  activity=activity_instance,
                                                                                  prefix='activity_attachment_formset_pre')
        # Process only if ALL forms are valid
        if all([
            organisation_people_activity_form.is_valid(),
            activity_attachment_formset.is_valid()
        ]):
            if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                # Save Organisation details
                organisation_people_activity = organisation_people_activity_form.save()

                # Save Attachments formset
                instances = activity_attachment_formset.save(commit=False)
                for instance in instances:
                    instance.activity = activity_instance
                activity_attachment_formset.save()

            return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation_people_activity_form': organisation_people_activity_form,
                'activity_attachment_formset': activity_attachment_formset,
            })


class OrganisationPeopleActivityPinView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationPeopleActivity
    form_class = ConfirmationForm
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def form_valid(self, form, *args, **kwargs):

        def ignored_switch(self, comment):
            return not comment.is_pinned

        # Switch value
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            activity = get_object_or_404(
                OrganisationPeopleActivity, pk=self.kwargs['pk'])
            activity.is_pinned = ignored_switch(self, activity)
            activity.save()

            if activity.is_pinned:
                messages.success(self.request, f'Comment pinned')
            else:
                messages.success(self.request, f'Comment unpinned')

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        activity = get_object_or_404(
            OrganisationPeopleActivity, pk=self.kwargs['pk'])

        if activity:
            if not activity.is_pinned:
                metacontext = {
                    'title': 'Pin Activity Record',
                    'icon': 'fa-thumbtack',
                    'text': f'Please confirm activity record pinning.',
                    'action_button_text': 'Pin',
                    'action_button_class': 'btn-success',
                }
            else:
                metacontext = {
                    'title': 'Unpin Activity Record',
                    'icon': 'fa-thumbtack',
                    'text': f'Please confirm activity record unpinning.',
                    'action_button_text': 'Unpin',
                    'action_button_class': 'btn-danger',
                }

        context['metacontext'] = metacontext
        return context
