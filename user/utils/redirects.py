from django.conf import settings


def get_user_landing_page(user):

    """
    Function generates landing URL for a user by various conditions.
    IMPORTANT: reverse should be used instead reverse_lazy, it required by the two-factor-auth
    :param user:
    :return:
    """
    from django.urls import reverse

    if user.is_staff and user.is_forced_onboard:
        return reverse('admin:staff_user_onboarding')

    if user.roles.filter(pk__in=[2, 1000]).exists():
        # Redirect "Military Team" and "Military Team Observer" to S&F Requests list
        redirect_url = reverse('admin:handling_requests')
    else:
        redirect_url = reverse(getattr(settings, 'LOGIN_REDIRECT_URL', 'admin:dashboard'))

    return redirect_url
