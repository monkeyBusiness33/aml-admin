from .client_notifications import handling_request_unable_to_support_notification
from handling.utils.fuel_booking_notifications import staff_fuel_booking_cancelled_notification
from ..models import (
    HandlingRequest,
    HandlingRequestMovement,
    HandlingRequestServices,
    AutoServiceProvisionForm,
    HandlingRequestAmendmentSession,
)


def reinstate_mission(handling_request, arrival_datetime=None, departure_datetime=None, author=None):
    """
    Reinstate S&F Request (un-cancel)
    :param handling_request: HandlingReqeust instance
    :param arrival_datetime: datetime instance
    :param departure_datetime: datetime instance
    :param author: Person instance
    :return:
    """
    if arrival_datetime and departure_datetime:
        HandlingRequestMovement.objects.filter(
            request_id=handling_request.id,
            direction__code='ARRIVAL').update(
            date=arrival_datetime
        )
        HandlingRequestMovement.objects.filter(
            request_id=handling_request.id,
            direction__code='DEPARTURE').update(
            date=departure_datetime
        )

    HandlingRequestServices.objects.filter(
        movement__in=handling_request.movement.all()
    ).update(booking_confirmed=None)

    AutoServiceProvisionForm.objects.filter(handling_request=handling_request).delete()
    HandlingRequestAmendmentSession.objects.filter(handling_request=handling_request).update(is_gh_opened=False)

    # Reset S&F Request details
    handling_request.is_handling_confirmed = False
    handling_request.cancelled = False
    handling_request.amended = False
    handling_request.created_by = author
    handling_request.save()
    HandlingRequest.objects.filter(pk=handling_request.pk).update(is_new=True)

    handling_request.activity_log.create(
        author=author,
        record_slug='sfr_reinstate',
        details='Servicing & Fueling Request has been reinstated',
    )

    if hasattr(handling_request, 'fuel_booking'):
        handling_request.fuel_booking.delete()
    from ..tasks import handling_request_send_fuel_team_booking_invite
    handling_request_send_fuel_team_booking_invite.delay(handling_request.id)

    from ..tasks import handling_request_submitted_staff_notification
    handling_request_submitted_staff_notification.apply_async(args=(handling_request.id,), countdown=2)


def unable_to_support_actions(handling_request, author=None):
    # Create history record
    handling_request.activity_log.create(
        record_slug='sfr_unable_to_support',
        details=f'S&F Request cancelled - Unable to Support',
        author=author,
    )
    # Generate notifications
    handling_request_unable_to_support_notification(handling_request.pk)
    staff_fuel_booking_cancelled_notification.delay(handling_request.pk)


def handling_request_cancel_actions(handling_request, author, auto_cancellation_reason=None,
                                    cancellation_grace_period=False):
    """
    Function cancels S&F Request and triggers required notifications
    :param handling_request:
    :param author:
    :return:
    """
    if handling_request.is_cancelable or cancellation_grace_period:
        handling_request.cancelled = True
        handling_request.amended = False
        handling_request.is_handling_confirmed = False
        handling_request.updated_by = author
        handling_request.save()

        # !!! Disabled due to implementation of the "Handling Booking Cancellation" functionality
        # if hasattr(handling_request, 'auto_spf'):
        #     handling_request.auto_spf.delete()

        from handling.utils.staff_notifications import staff_cancellation_notifications
        staff_cancellation_notifications.delay(
            handling_request=handling_request.pk,
            author=getattr(author, 'pk', None),
            auto_cancellation_reason=auto_cancellation_reason
        )

        handling_request.activity_log.create(
            record_slug='sfr_cancelled',
            author=author,
            details='Servicing & Fueling Request cancelled'
                    + (f" automatically due to {auto_cancellation_reason}" if auto_cancellation_reason else ""),
        )

    return handling_request
