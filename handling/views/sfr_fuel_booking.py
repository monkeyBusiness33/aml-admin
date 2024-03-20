from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import PassRequestMixin
from bootstrap_modal_forms.mixins import is_ajax
from django.shortcuts import get_object_or_404
from django.views.generic import FormView

from core.forms import ConfirmationForm
from handling.forms.sfr_fuel import FuelBookingConfirmationForm, FuelReleaseForm
from handling.mixins import GetHandlingRequestMixinOps
from handling.models import HandlingRequestFuelBooking, HandlingRequest
from user.mixins import AdminPermissionsMixin


class HandlingRequestFuelBookingConfirmationView(PassRequestMixin, GetHandlingRequestMixinOps, FormView):
    template_name = 'fuel_booking_confirmation.html'
    model = HandlingRequestFuelBooking
    form_class = FuelBookingConfirmationForm

    is_fuel_booking_confirmed = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.is_fuel_booking_confirmed = getattr(self.handling_request, 'is_fuel_booking_confirmed')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        if hasattr(self.handling_request, 'fuel_booking'):
            instance = self.handling_request.fuel_booking
        else:
            instance = self.model(handling_request=self.handling_request)

        kwargs.update({'instance': instance})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_fuel_booking_confirmed'] = self.is_fuel_booking_confirmed
        context['dla_contract'] = getattr(self.handling_request, 'fuel_dla_contract', None)
        return context

    def form_valid(self, form):
        if self.is_fuel_booking_confirmed:
            form.add_error(None, 'Fuel booking already processed for this S&F Request')
            for field in form.fields:
                form.fields[field].disabled = True
            return super().form_invalid(form)

        form.instance.is_confirmed = True
        form.save()
        return super().form_valid(form)


class HandlingRequestFuelBookingStaffUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_request/_modal_fuel_booking.html'
    model = HandlingRequestFuelBooking
    form_class = FuelBookingConfirmationForm
    permission_required = ['handling.p_update']

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['handling_request_id'])

    def get_object(self, queryset=None):
        try:
            return self.handling_request.fuel_booking
        except AttributeError:
            fuel_booking = HandlingRequestFuelBooking(
                handling_request=self.handling_request,
                processed_by=getattr(self, 'person').fullname,
            )
            return fuel_booking

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Fuel Booking Confirmation',
            'icon': 'fa-check',
            'form_id': 'fuel_booking_confirmation',
            'action_button_class': 'btn-success',
            'action_button_text': 'Confirm Booking',
            'cancel_button_class': 'btn-gray-200',
        }

        dla_contract = getattr(self.handling_request, 'fuel_dla_contract', None)
        if dla_contract:
            metacontext['alerts'] = [
                {
                    'text': f'Please note that fuel at this location is contracted to '
                            f'<b>{dla_contract.supplier.full_repr}</b>',
                    'class': 'alert-danger',
                    'icon': 'exclamation-triangle',
                    'position': 'top',
                }
            ]

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        form.instance.is_confirmed = True

        form.instance.handling_request.updated_by = getattr(self, 'person')
        form.instance.handling_request.fuel_required = form.cleaned_data.get('fuel_required', None)
        form.instance.handling_request.fuel_quantity = form.cleaned_data.get('fuel_quantity', None)
        form.instance.handling_request.fuel_unit = form.cleaned_data.get('fuel_unit', None)
        form.instance.handling_request.fuel_prist_required = form.cleaned_data.get('fuel_prist_required', None)
        # Saving is happening in HandlingRequestFuelBooking save() method

        return super().form_valid(form)


class HandlingRequestFuelReleaseUploadView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestFuelBooking
    form_class = FuelReleaseForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Fuel Release Upload',
            'icon': 'fa-upload',
            'action_button_class': 'btn-success',
            'action_button_text': 'Upload',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestFuelReleaseRemoveView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    permission_required = ['handling.p_update']
    fuel_booking = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.fuel_booking = get_object_or_404(HandlingRequestFuelBooking, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Remove Fuel Release',
            'icon': 'fa-trash',
            'text': 'Please confirm that you want to remove "Fuel Release" file from the S&F Request',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Remove',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        request_person = getattr(self.request.user, 'person')
        if not is_ajax(self.request.META):
            self.fuel_booking.updated_by = request_person
            self.fuel_booking.fuel_release.delete()
        return super().form_valid(form)
