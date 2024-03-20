from bootstrap_modal_forms.mixins import is_ajax
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.conf import settings

from handling.forms.sfr_payload import HandlingRequestPassengersPayloadForm, \
    HandlingRequestPassengersPayloadBaseFormSet, HandlingRequestCargoPayloadForm, HandlingRequestCargoPayloadBaseFormSet
from handling.models import HandlingRequest, HandlingRequestPassengersPayload, HandlingRequestCargoPayload
from handling.utils.handling_request_payload import passengers_payload_update_movements, cargo_payload_auto_services


class HandlingRequestPayloadMixin(TemplateView):
    template_name = 'handling_request/_modal_payload.html'

    handling_request = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = HandlingRequest.objects.get(pk=self.kwargs['pk'])

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_metacontext(self):
        metacontext = {
            'title': 'Manage Payload',
            'action_button_class': 'btn-secondary',
            'action_button_text': 'Update Payload',
        }
        return metacontext

    def get_passengers_payload_formset(self):
        if self.handling_request.passengers_count:
            passengers_count = self.handling_request.passengers_count
        else:
            passengers_count = 0

        passengers_payload_formset = modelformset_factory(
            HandlingRequestPassengersPayload,
            min_num=passengers_count,
            extra=passengers_count + 10,
            can_delete=False,
            form=HandlingRequestPassengersPayloadForm,
            formset=HandlingRequestPassengersPayloadBaseFormSet,
            fields=['identifier', 'gender', 'weight', 'note', 'is_arrival', 'is_departure', ]
        )
        return passengers_payload_formset

    def get_cargo_payload_formset(self):
        passengers_payload_formset = modelformset_factory(
            HandlingRequestCargoPayload,
            extra=30,
            can_delete=True,
            form=HandlingRequestCargoPayloadForm,
            formset=HandlingRequestCargoPayloadBaseFormSet,
            fields=['description',
                    'length', 'width', 'height', 'weight', 'quantity',
                    'is_dg', 'note', 'is_arrival', 'is_departure', ]
        )
        return passengers_payload_formset

    def get(self, request, *args, **kwargs):
        return self.render_to_response({
            'handling_request': self.handling_request,
            'metacontext': self.get_metacontext(),
            'pax_payload_formset': self.get_passengers_payload_formset()(
                handling_request=self.handling_request,
                prefix='pax_payload_formset_pre'),
            'cargo_payload_formset': self.get_cargo_payload_formset()(
                handling_request=self.handling_request,
                prefix='cargo_payload_formset_pre'),
        })

    def post(self, request, *args, **kwargs):
        pax_payload_formset = self.get_passengers_payload_formset()(request.POST or None,
                                                                    handling_request=self.handling_request,
                                                                    prefix='pax_payload_formset_pre')

        cargo_payload_formset = self.get_cargo_payload_formset()(request.POST or None,
                                                                 handling_request=self.handling_request,
                                                                 prefix='cargo_payload_formset_pre')

        # Process only if ALL forms are valid
        if all([
            pax_payload_formset.is_valid(),
            cargo_payload_formset.is_valid(),
        ]):
            if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':

                instances = pax_payload_formset.save(commit=False)
                for instance in instances:
                    instance.handling_request = self.handling_request
                pax_payload_formset.save()

                instances = cargo_payload_formset.save(commit=False)
                for instance in instances:
                    instance.handling_request = self.handling_request
                cargo_payload_formset.save()

                self.handling_request.activity_log.create(
                    record_slug='sfr_payload_updated',
                    author=getattr(self, 'person'),
                    details='Payload has been updated'
                )

                passengers_payload_update_movements(handling_request=self.handling_request,
                                                    author=getattr(self, 'person'))
                cargo_payload_auto_services(handling_request=self.handling_request)

                if pax_payload_formset.has_changed():
                    # Set "fake" AMENDED status to attract attention
                    HandlingRequest.objects.filter(pk=self.handling_request.pk).update(
                        amended=True,
                    )

            return HttpResponseRedirect(self.get_success_url())
        else:
            if settings.DEBUG:
                print(
                    pax_payload_formset.errors if pax_payload_formset else '',
                    cargo_payload_formset.errors if cargo_payload_formset else '',
                )
            # Render forms with errors
            return self.render_to_response({
                'handling_request': self.handling_request,
                'metacontext': self.get_metacontext(),
                'pax_payload_formset': pax_payload_formset,
                'cargo_payload_formset': cargo_payload_formset,
            })
