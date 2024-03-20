from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import RedirectView

from user.utils.redirects import get_user_landing_page


class IndexView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self):
        redirect_url = get_user_landing_page(self.request.user)
        return redirect_url
