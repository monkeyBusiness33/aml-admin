from user.backends import AMLUserBackend


class DodUserBackend(AMLUserBackend):
    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        Reject user who does not have at least one organisation position with
        application access.
        """
        is_active = getattr(user, 'is_active', None)
        if is_active or is_active is None:
            is_active_res = True
        else:
            is_active_res = False

        return all([is_active_res, user.is_dod_portal_user])
