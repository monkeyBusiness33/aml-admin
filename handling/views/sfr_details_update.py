from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.utils import timezone

from core.forms import ConfirmationForm
from handling.forms.sfr_admin_editing import HandlingRequestAdminEditingForm
from handling.forms.sfr_aircraft import HandlingRequestConfirmTailNumberForm
from handling.forms.sfr_crew import HandlingRequestCrewFormSet
from handling.forms.sfr_parking import HandlingRequestParkingConfirmationForm
from handling.forms.sfr_update import HandlingRequestCallsignUpdateForm, HandlingRequestUpdateTailNumberForm, \
    HandlingRequestMissionNumberUpdateForm, HandlingRequestTypeUpdateForm, HandlingRequestUpdateApacsNumberForm, \
    HandlingRequestAirCardDetailsForm, HandlingRequestAssignedTeamMemberUpdateForm, HandlingRequestUnableToSupportForm
from handling.models import HandlingRequest, HandlingRequestCrew, HandlingRequestRecurrence, HandlingRequestServices
from handling.shared_views.apacs_url import ApacsUrlUpdateMixin
from handling.shared_views.communications import HandlingRequestConversationCreateMixin
from handling.shared_views.handling_request_aircraft import UpdateAircraftTypeMixin
from handling.shared_views.handling_request_aog import HandlingRequestAogMixin, HandlingRequestAircraftServiceableMixin
from handling.shared_views.handling_request_cancellation import HandlingRequestCancelMixin
from handling.shared_views.payload import HandlingRequestPayloadMixin
from handling.shared_views.recurrence import UpdateRecurrenceMixin, CancelRecurrenceMixin
from handling.utils.handling_request_func import unable_to_support_actions
from handling.utils.handling_request_update_or_create import update_or_create_sfr
from handling.utils.sfr_ground_handling_confirmation import sfr_confirm_ground_handling
from user.mixins import AdminPermissionsMixin


class HandlingRequestCallsignUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestCallsignUpdateForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        handling_request = self.get_object()
        context['handling_request'] = handling_request

        metacontext = {
            'title': f'Update Mission Callsign',
            'icon': 'fa-fighter-jet',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestConfirmCallsignView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    success_message = 'Callsign amendment confirm'
    permission_required = ['core.ops_handling_update_callsign']

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Confirm Callsign Amendment',
            'icon': 'fa-check',
            'text': f'This action will confirm callsign amendment',
            'action_button_class': 'btn-success',
            'action_button_text': 'Confirm',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            self.handling_request.updated_by = getattr(self, 'person')
            self.handling_request.save()
        return super().form_valid(form)


class HandlingRequestUpdateTailNumberView(AdminPermissionsMixin, BSModalUpdateView):
    """
    View update Handling Request tail number and set required state for included services.
    """
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdateTailNumberForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Update tail number for {obj.callsign}',
            'icon': 'fa-id-card',
            'text': f'Submitting new tail number will reset services confirmation state to unconfirmed',
            'form_id': 'update_tail_number_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
            'js_scripts': [
                static('js/sfr_update_tail_number.js'),
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestConfirmTailNumberView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_request/_modal_confirm_tail_number.html'
    model = HandlingRequest
    form_class = HandlingRequestConfirmTailNumberForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Confirm Tail Number for {obj.callsign}',
            'icon': 'fa-id-card',
            'form_id': 'confirm_tail_number_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Confirm',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestMissionNumberUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestMissionNumberUpdateForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        handling_request = self.get_object()
        context['handling_request'] = handling_request

        metacontext = {
            'title': f'Update Mission Number',
            'icon': 'fa-hashtag',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestTypeUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestTypeUpdateForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        handling_request = self.get_object()
        context['handling_request'] = handling_request

        metacontext = {
            'title': f'Update Mission Type',
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


class HandlingRequestUpdateAssignedPersonView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'handling_request/_modal_assigned_crew.html'
    model = HandlingRequestCrew
    form_class = HandlingRequestCrewFormSet
    permission_required = ['handling.p_update']
    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'handling_request': self.handling_request})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Manage Assigned Crew',
            'icon': 'fa-users',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.save()
            self.handling_request.updated_by = getattr(self, 'person')
            self.handling_request.activity_log.create(
                record_slug='sfr_mission_crew_update',
                author=getattr(self, 'person'),
                details=f'Mission Crew has been updated',
            )
            self.handling_request.save()
        return super().form_valid(form)


class HandlingRequestUpdateApacsNumberView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdateApacsNumberForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update Diplomatic Clearance',
            'icon': 'fa-hashtag',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestUpdateApacsUrlView(AdminPermissionsMixin, ApacsUrlUpdateMixin):
    permission_required = ['handling.p_update']


class HandlingRequestAirCardDetailsView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_request/_modal_aircard.html'
    model = HandlingRequest
    form_class = HandlingRequestAirCardDetailsForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        handling_request = self.get_object()
        context['handling_request'] = handling_request

        metacontext = {
            'title': f'AIR Card Details',
            'icon': 'fa-credit-card',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestAssignedTeamMemberUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestAssignedTeamMemberUpdateForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        handling_request = self.get_object()
        context['handling_request'] = handling_request

        metacontext = {
            'title': f'Update Assigned Military Team Member',
            'icon': 'fa-user',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestCancelView(AdminPermissionsMixin, HandlingRequestCancelMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])


class HandlingRequestUnableToSupportView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUnableToSupportForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Decline Servicing & Fueling Request',
            'icon': 'fa-ban',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Decline',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        form.instance.is_unable_to_support = True
        response = super().form_valid(form)

        if not is_ajax(self.request.META):
            unable_to_support_actions(
                handling_request=form.instance,
                author=getattr(self.request.user, 'person', None),
            )

        return response


class HandlingRequestAogView(AdminPermissionsMixin, HandlingRequestAogMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])


class HandlingRequestAircraftServiceableView(AdminPermissionsMixin, HandlingRequestAircraftServiceableMixin):
    permission_required = ['handling.p_update']


class HandlingRequestParkingConfirmationView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestParkingConfirmationForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'form_id': 'booking_confirmation',
            'title': f'Confirm Parking',
            'icon': 'fa-check',
            'action_button_text': 'Confirm',
            'action_button_class': 'btn-success',
            'js_scripts': [
                static('js/sfr_parking_confirmation.js'),
            ],
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestUpdateAircraftTypeView(AdminPermissionsMixin, UpdateAircraftTypeMixin):
    permission_required = ['handling.p_update']


class HandlingRequestUpdateRecurrenceView(AdminPermissionsMixin, UpdateRecurrenceMixin):
    permission_required = ['handling.p_update']


class HandlingRequestCancelRecurrenceView(AdminPermissionsMixin, CancelRecurrenceMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.recurrence = HandlingRequestRecurrence.objects.get(pk=self.kwargs['pk'])
        except HandlingRequestRecurrence.DoesNotExist:
            raise Http404


class HandlingRequestPayloadUpdateView(AdminPermissionsMixin, HandlingRequestPayloadMixin):
    permission_required = ['handling.p_update']


class HandlingRequestConversationCreateView(AdminPermissionsMixin, HandlingRequestConversationCreateMixin):
    permission_required = ['handling.p_dod_comms']


class HandlingRequestAdminEditingView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'handling_request/_modal_admin_edit.html'
    form_class = HandlingRequestAdminEditingForm
    permission_required = ['handling.p_admin_edit']

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'handling_request': self.handling_request})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'S&F Request Admin Editing',
            'icon': 'fa-screwdriver-wrench',
            'action_button_text': 'Update',
            'action_button_class': 'btn-success',
        }

        if not self.handling_request.is_admin_edit_available:
            context['form'] = None
            metacontext['hide_action_button'] = True
            metacontext['text_danger'] = "Admin Edit is not available for this S&F Request"

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        arrival_date = form.cleaned_data['arrival_date']
        arrival_is_local_timezone = form.cleaned_data['arrival_is_local_timezone']
        departure_date = form.cleaned_data['departure_date']
        departure_is_local_timezone = form.cleaned_data['departure_is_local_timezone']
        confirm_all_services = form.cleaned_data['confirm_all_services']
        retain_fuel_order = form.cleaned_data['retain_fuel_order']
        confirm_ground_handling = form.cleaned_data['confirm_ground_handling']

        arrival_movement_data = None
        departure_movement_data = None

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if {'arrival_date', 'arrival_is_local_timezone'}.intersection(form.changed_data):
                arrival_movement_data = {
                    'date': arrival_date,
                    'is_datetime_local': arrival_is_local_timezone,
                    'movement_meta_retain_fuel_order': retain_fuel_order,
                    'movement_meta_retain_gh_confirmation': confirm_ground_handling,
                }
            if {'departure_date', 'departure_is_local_timezone'}.intersection(form.changed_data):
                departure_movement_data = {
                    'date': departure_date,
                    'is_datetime_local': departure_is_local_timezone,
                    'movement_meta_retain_fuel_order': retain_fuel_order,
                    'movement_meta_retain_gh_confirmation': confirm_ground_handling,
                }
            if {'arrival_date', 'arrival_is_local_timezone', 'departure_date',
                    'departure_is_local_timezone'}.intersection(form.changed_data) and retain_fuel_order:
                self.handling_request.activity_log.create(
                    author=getattr(self, 'person'),
                    details='Fuel Order is retained'
                )

            self.handling_request.activity_log.create(
                author=getattr(self, 'person'),
                details='Admin Edit Session: Start'
            )

            if confirm_ground_handling:
                # Create "AutoSPF" (aka Ground Handling Confirmation Request)
                sfr_confirm_ground_handling(
                    handling_request=self.handling_request,
                    author=getattr(self, 'person'),
                    sent_externally=True,
                )
                self.handling_request.is_handling_confirmed = True

            if arrival_movement_data or departure_movement_data or confirm_ground_handling:
                update_or_create_sfr(author=getattr(self, 'person'),
                                     handling_request=self.handling_request,
                                     arrival_movement_data=arrival_movement_data,
                                     departure_movement_data=departure_movement_data)

            if confirm_all_services:
                HandlingRequestServices.objects.filter(
                    movement__request=self.handling_request,
                ).update(
                    booking_confirmed=True,
                    updated_by=getattr(self, 'person'),
                    updated_at=timezone.now(),
                )
                self.handling_request.activity_log.create(
                    author=getattr(self, 'person'),
                    details='All services has been confirmed'
                )

            self.handling_request.activity_log.create(
                author=getattr(self, 'person'),
                details='Admin Edit Session: End'
            )

        return super().form_valid(form)
