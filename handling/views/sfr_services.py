from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalFormView, BSModalUpdateView
from bootstrap_modal_forms.mixins import is_ajax
from django.contrib import messages
from django.templatetags.static import static
from django.utils import timezone

from core.forms import ConfirmationForm
from handling.forms.sfr_services import HandlingRequestAddServiceForm, HandlingServicesConfirmationForm, \
    HandlingServiceConfirmationForm, HandlingServiceInternalNoteForm
from handling.models import HandlingRequestServices, HandlingRequestMovement, HandlingRequest
from user.mixins import AdminPermissionsMixin


class HandlingRequestAddServiceView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestServices
    permission_required = ['handling.p_update']
    form_class = HandlingRequestAddServiceForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        movement = HandlingRequestMovement.objects.get(pk=self.kwargs['pk'])

        # Inject movement object into the form context
        kwargs.update({'movement': movement})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        movement = HandlingRequestMovement.objects.get(pk=self.kwargs['pk'])

        if movement.request.customer_organisation.is_military:
            modal_text = f'This form helps you create Custom DLA service and add it to the current "Handling Request"'
        else:
            modal_text = f'This form add selected service to the Handling Request'

        metacontext = {
            'title': f'Add Service to Servicing & Fueling Request',
            'icon': 'fa-plus',
            'text': modal_text,
            'form_id': 'add_services_to_handling_request',
            'action_button_class': 'btn-success',
            'action_button_text': 'Add',
            'cancel_button_class': 'btn-gray-200',
            'js_scripts': [
                static('js/sfr_add_service_modal.js'),
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestDeleteServiceView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestServices
    form_class = ConfirmationForm
    permission_required = ['handling.p_update']
    success_message = 'Service has been removed from request'

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Remove {obj.service.name}',
            'icon': 'fa-trash-alt',
            'text': f'This form remove service "{obj.service.name}" from the handling request',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Remove',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.object.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestsConfirmView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    permission_required = ['handling.p_update']

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        scope = self.kwargs['scope']

        if scope == 'arrival' or scope == 'departure':
            self.handling_request = HandlingRequest.objects.get(movement__id=self.kwargs['pk'])
        if scope == 'service':
            self.handling_request = HandlingRequest.objects.filter(movement__hr_services__id=self.kwargs['pk']).first()

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        scope = self.kwargs['scope']

        # Pass object into the Form
        if scope == 'arrival' or scope == 'departure':
            self.object = HandlingRequest.objects.get(movement__id=self.kwargs['pk'])

        if scope == 'service':
            self.object = HandlingRequestServices.objects.get(pk=self.kwargs['pk'])

        if hasattr(self, 'object'):
            kwargs.update({'instance': self.object})

        return kwargs

    def get_form_class(self):
        """Return the form class to use."""
        scope = self.kwargs['scope']

        if scope == 'arrival' or scope == 'departure':
            form_class = HandlingServicesConfirmationForm
        elif scope == 'service':
            form_class = HandlingServiceConfirmationForm

        return form_class

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        scope = self.kwargs['scope']

        # Default confirmation dialog format
        multi_button = True
        if scope == 'arrival':
            question_text = f'<b>all</b> services requested on arrival'
        elif scope == 'departure':
            question_text = f'<b>all</b> services requested on departure'
        elif scope == 'service':
            question_text = f'<b>{self.object.service.name}</b>'

        metacontext = {
            'form_id': 'booking_confirmation',
            'title': f'Confirm {question_text}',
            'icon': 'fa-check',
            'multi_button': multi_button,
            'action_button_text': 'Confirm',
            'action_button_class': 'btn-success',
            'js_scripts': [
                static('js/sfr_handler_quick_create.js'),
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        scope = self.kwargs['scope']

        # Fetch "Confirm" or "Decline" button was selected in the dialog
        if 'multi_button' in form.cleaned_data:
            selection = form.cleaned_data['multi_button']

        # Validate Handling Agent selection on service confirmation
        if self.handling_request.is_ground_handling_confirmation_applicable:
            if scope == 'service' or scope == 'arrival' or scope == 'departure':
                handling_agent = form.cleaned_data.get('handling_agent')
                if selection and not handling_agent:
                    form.add_error('handling_agent',
                                   'To confirm service booking you need to select Handling Agent')
                    return super().form_invalid(form)

        if not is_ajax(self.request.META):
            if scope == 'arrival' or scope == 'departure':
                handling_agent = form.cleaned_data.get('handling_agent')

                # Update Handling Request 'handling_agent' field
                handling_request = HandlingRequest.objects.filter(movement__id=self.kwargs['pk']).first()
                movement = HandlingRequestMovement.objects.get(pk=self.kwargs['pk'])
                handling_request.handling_agent = handling_agent
                handling_request.updated_by = getattr(self, 'person')
                handling_request.save()

                # Update requested Handling Services
                HandlingRequestServices.objects \
                    .filter(movement_id=self.kwargs['pk']) \
                    .exclude(booking_confirmed__isnull=False) \
                    .update(
                        booking_confirmed=selection,
                        updated_at=timezone.now(),
                        updated_by=getattr(self.request.user, 'person'))

                # # Add HandlingReqeust Actions record
                selection_text = 'confirmed' if selection else 'declined'

                movement.activity_log.create(
                    author=getattr(self, 'person'),
                    record_slug='sfr_movement_services_confirmation',
                    details=f'All services has been {selection_text}'
                )

            elif scope == 'service':
                handling_agent = form.cleaned_data.get('handling_agent')
                handling_request_service = form.save(commit=False)

                handling_request = handling_request_service.movement.request
                movement = handling_request_service.movement
                handling_request.handling_agent = handling_agent
                handling_request.updated_by = getattr(self, 'person')
                handling_request.save()

                handling_request_service.booking_confirmed = selection
                handling_request_service.updated_by = getattr(self.request.user, 'person')
                handling_request_service.save()

                # Add HandlingReqeust Actions record
                service_name = getattr(handling_request_service.service, 'name', None)
                selection_text = 'confirmed' if selection else 'declined'

                movement.activity_log.create(
                    author=getattr(self, 'person'),
                    record_slug='sfr_movement_service_confirmation',
                    data={'service_name': service_name},
                    details=f'"{service_name}" has been {selection_text}'
                )

            messages.success(self.request, f'Handling Request Updated')
        return super().form_valid(form)


class HandlingServiceInternalNoteView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestServices
    form_class = HandlingServiceInternalNoteForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update Service Details',
            'icon': 'fa-edit',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)
