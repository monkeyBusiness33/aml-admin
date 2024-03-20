from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import PassRequestMixin
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, UpdateView

from handling.forms.sfr_create import HandlingRequestForm
from handling.forms.sfr_reinstate import HandlingRequestReinstateForm
from handling.models import HandlingRequest
from handling.shared_views.handling_request_aircraft import HandlingRequestAircraftCreateMixin
from organisation.models import Organisation
from user.mixins import AdminPermissionsMixin


class HandlingRequestCreateView(AdminPermissionsMixin, PassRequestMixin, SuccessMessageMixin, CreateView):
    template_name = 'handling_request_create.html'
    model = HandlingRequest
    form_class = HandlingRequestForm
    context_object_name = 'handling_request'
    permission_required = ['handling.p_create']
    success_message = 'Servicing & Fueling Request successfully created'

    def get_success_url(self):
        return reverse_lazy('admin:handling_request', kwargs={'pk': self.object.pk})


class HandlingRequestCopyView(AdminPermissionsMixin, PassRequestMixin, SuccessMessageMixin, CreateView):
    template_name = 'handling_request_create.html'
    model = HandlingRequest
    form_class = HandlingRequestForm
    context_object_name = 'handling_request'
    permission_required = ['handling.p_create']
    success_message = 'Servicing & Fueling Request successfully created'

    original_request = None

    def get_success_url(self):
        return reverse_lazy('admin:handling_request', kwargs={'pk': self.object.pk})

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        handling_request_id = self.kwargs.get('pk')
        if handling_request_id:
            self.original_request = get_object_or_404(HandlingRequest, pk=handling_request_id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'original_request': self.original_request})
        return kwargs


class HandlingRequestUpdateView(AdminPermissionsMixin, PassRequestMixin, UpdateView):
    template_name = 'handling_request_create.html'
    queryset = HandlingRequest.objects.with_status()
    form_class = HandlingRequestForm
    context_object_name = 'handling_request'
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return reverse_lazy('admin:handling_request_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        arrival_movement = obj.movement.filter(direction_id='ARRIVAL').first()
        departure_movement = obj.movement.filter(direction_id='DEPARTURE').first()

        context['arrival_movement'] = arrival_movement
        context['departure_movement'] = departure_movement
        return context


class HandlingRequestReinstateView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'handling_request/_modal_reinstate.html'
    form_class = HandlingRequestReinstateForm
    permission_required = ['handling.p_update']
    handling_request = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'handling_request': self.handling_request})
        return kwargs

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.handling_request.arrival_movement.date <= timezone.now():
            text = f'Servicing & Fueling Request have <b>movement dates in past</b>, ' \
                   f'please set new dates and confirm reinstating.'
        else:
            text = f'Please confirm Servicing & Fueling Request reinstating.'

        metacontext = {
            'title': 'Reinstate Servicing & Fueling Request',
            'icon': 'fa-trash-restore',
            'text': text,
            'action_button_text': 'Reinstate',
            'action_button_class': 'btn-secondary',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        form.save()
        messages.success(self.request, f'Servicing & Fueling Request has been reinstated')
        return super().form_valid(form)


class HandlingRequestAircraftCreateView(AdminPermissionsMixin, HandlingRequestAircraftCreateMixin):
    permission_required = ['handling.p_create']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = get_object_or_404(Organisation, pk=self.kwargs['operator_id'])
