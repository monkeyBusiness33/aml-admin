import json

from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalFormView, BSModalUpdateView
from bootstrap_modal_forms.mixins import is_ajax
from ajax_datatable.views import AjaxDatatableView
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button
from handling.models import HandlingService, HandlingRequest
from mission.models import Mission
from organisation.models.organisation import Organisation
from supplier.models import FuelAgreement
from user.mixins import AdminPermissionsMixin
from user.models.person import Person
from ..models import *
from ..forms import *


class CommentsAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Comment
    search_values_separator = '+'
    initial_order = [["is_pinned", "desc"], ["created_at", "desc"], ]
    permission_required = []

    def get_initial_queryset(self, request=None):
        entity_slug = self.kwargs.get('entity_slug')
        entity_pk = self.kwargs.get('entity_pk')

        if entity_slug == 'organisation':
            qs = Comment.objects.filter(organisation_id=entity_pk)
        elif entity_slug == 'person':
            qs = Comment.objects.filter(person_id=entity_pk)
        elif entity_slug == 'handling_service':
            qs = Comment.objects.filter(handling_service_id=entity_pk)
        elif entity_slug == 'fuel_agreement':
            qs = Comment.objects.filter(supplier_fuel_agreement_id=entity_pk)
        elif entity_slug == 'handling_request':
            qs = Comment.objects.filter(handling_request_id=entity_pk)
        elif entity_slug == 'mission':
            qs = Comment.objects.filter(mission_id=entity_pk)
        else:
            qs = Comment.objects.none()

        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'text', 'visible': True, 'searchable': False, 'width': '800px'},
        {'name': 'created_at', 'visible': True, 'choices': True, 'searchable': False, },
        {'name': 'author', 'title': 'Author', 'foreign_field': 'author__details__first_name',
            'visible': True, },
        {'name': 'is_pinned', 'visible': True, 'searchable': False, },
        {'name': 'actions', 'title': '', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions_column'},
    ]

    def customize_row(self, row, obj):
        row['created_at'] = obj.created_at.strftime("%Y-%m-%d %H:%M")
        row['author'] = f'{obj.author.fullname}'
        if obj.is_pinned:
            pinned_class = 'text-success fa-thumbtack'
        else:
            pinned_class = 'text-gray-300 fa-thumbtack'

        pin_btn = get_datatable_actions_button(button_text='',
                                               button_url=reverse_lazy(
                                                   'admin:comment_pin', kwargs={'pk': obj.pk}),
                                               button_class=pinned_class,
                                               button_active=True,
                                               button_modal=True,
                                               modal_validation=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:comment_delete', kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=obj.can_be_removed_by(self.request.user),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['is_pinned'] = pin_btn
        row['actions'] = delete_btn
        return


class CommentCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = Comment
    form_class = CommentForm
    success_message = 'Comment added successfully'
    permission_required = ['core.p_comments_create']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        entity_slug = self.kwargs.get('entity_slug')
        entity_pk = self.kwargs.get('entity_pk')
        instance = self.model(author=self.request.user.person)

        if entity_slug == 'organisation':
            organisation = get_object_or_404(Organisation, pk=entity_pk)
            instance.organisation = organisation
        elif entity_slug == 'person':
            person = get_object_or_404(Person, pk=entity_pk)
            instance.person = person
        elif entity_slug == 'handling_service':
            handling_service = get_object_or_404(HandlingService, pk=entity_pk)
            instance.handling_service = handling_service
        elif entity_slug == 'fuel_agreement':
            fuel_agreement = get_object_or_404(FuelAgreement, pk=entity_pk)
            instance.supplier_fuel_agreement = fuel_agreement
        elif entity_slug == 'handling_request':
            instance.handling_request = get_object_or_404(HandlingRequest, pk=entity_pk)
        elif entity_slug == 'mission':
            instance.mission = get_object_or_404(Mission, pk=entity_pk)

        kwargs.update({'instance': instance})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add New Comment',
            'icon': 'fa-comment-alt',
        }

        context['metacontext'] = metacontext
        return context


class CommentDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = Comment
    form_class = ConfirmationForm
    success_message = 'Comment has been deleted'

    def has_permission(self):
        # Allow remove any comment for user with permission
        if self.request.user.has_perm('core.p_comments_moderate'):
            return True
        # Allow remove user own comments
        if self.person == self.get_object().author:
            return True

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete Comment',
            'text': f'Are you sure you want to delete this comment?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context


class CommentPinView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = Comment
    form_class = ConfirmationForm
    permission_required = []

    comment = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.comment = get_object_or_404(Comment, pk=self.kwargs['pk'])

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.comment.is_pinned:
            metacontext = {
                'title': 'Pin Comment',
                'icon': 'fa-thumbtack',
                'text': f'Please confirm comment pinning.',
                'action_button_text': 'Pin',
                'action_button_class': 'btn-success',
            }
        else:
            metacontext = {
                'title': 'Unpin Comment',
                'icon': 'fa-thumbtack',
                'text': f'Please confirm comment unpinning.',
                'action_button_text': 'Unpin',
                'action_button_class': 'btn-danger',
            }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):

        # Switch value
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            self.comment.is_pinned = not self.comment.is_pinned
            self.comment.save()

            if self.comment.is_pinned:
                messages.success(self.request, f'Comment pinned')
            else:
                messages.success(self.request, f'Comment unpinned')

        return super().form_valid(form)


from django.views import View
from django.http import HttpResponse

class CommentReadView(AdminPermissionsMixin, View):
    template_name = 'includes/_modal_form.html'
    model = Comment
    permission_required = []

    comment = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.comment = get_object_or_404(Comment, pk=self.kwargs['pk'])

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def post(self, *args, **kwargs):
        # Switch value
        if is_ajax(self.request.META):
            read_status = self.comment.read_statuses.filter(person=self.request.user.person).last()

            if read_status is None:
                # If a status doesn't exist yet, create a default one
                read_status = CommentReadStatus.objects.create(
                    person=self.request.user.person,
                    comment=self.comment
                )
            else:
                # Otherwise toggle the value of is_read
                read_status.is_read = not read_status.is_read
                read_status.save()

            return HttpResponse(json.dumps({'is_read': read_status.is_read}), status=200)

