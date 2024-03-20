from bootstrap_modal_forms.mixins import is_ajax
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from organisation.models import OrganisationPeople
from user.forms import StaffUserOnboardingPersonDetailsForm, StaffUserOnboardingPersonPositionForm
from user.mixins import AdminPermissionsMixin
from user.utils.redirects import get_user_landing_page


class StaffUserOnboardingView(AdminPermissionsMixin, TemplateView):
    template_name = 'staff_user_onboarding.html'
    permission_required = []

    user = None
    person = None
    person_details = None
    person_position = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.user = getattr(self.request, 'user')
        self.person = getattr(self.user, 'person')
        self.person_details = getattr(self.person, 'details')

        # Find existing position
        self.person_position = OrganisationPeople.objects.filter(
            person=self.person,
            organisation_id=100000000,
        ).first()

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get(self, request, *args, **kwargs):
        if not self.user.is_forced_onboard:
            return HttpResponseRedirect(get_user_landing_page(self.request.user))
        return self.render_to_response({
            'person_details_form': StaffUserOnboardingPersonDetailsForm(
                instance=self.person_details,
                prefix='person_details_form_pre'),
            'person_position_form': StaffUserOnboardingPersonPositionForm(
                instance=self.person_position,
                prefix='person_position_form_pre'),
        })

    def post(self, request, *args, **kwargs):
        person_details_form = StaffUserOnboardingPersonDetailsForm(request.POST or None,
                                                                   instance=self.person_details,
                                                                   prefix='person_details_form_pre')
        person_position_form = StaffUserOnboardingPersonPositionForm(request.POST or None,
                                                                     instance=self.person_position,
                                                                     prefix='person_position_form_pre')

        # Process only if ALL forms are valid
        if all([
            person_details_form.is_valid(),
            person_position_form.is_valid(),
        ]):
            if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                person_details_form.save()
                person_position_form.save()
                self.user.is_forced_onboard = False
                self.user.save()

                messages.success(self.request, "Your profile updated")

            return HttpResponseRedirect(get_user_landing_page(self.request.user))
        else:
            if settings.DEBUG:
                print(
                    person_details_form.errors if person_details_form else '',
                    person_position_form.errors if person_position_form else '',
                )
            # Render forms with errors
            return self.render_to_response({
                'person_details_form': person_details_form,
                'person_position_form': person_position_form,
            })
