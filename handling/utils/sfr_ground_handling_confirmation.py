from handling.utils.spf_auto import generate_auto_spf_email, send_ground_handling_spf_amendment_email


def sfr_confirm_ground_handling(handling_request, author, sent_externally=True, email_cc_list=None,
                                departure_update_only=False):
    """
    This function confirms Ground Handling for the S&F Request
    (This is only template with basic functionality, needs moving functionality from SendHandlingRequestView.form_valid)
    :param handling_request:
    :param author:
    :param sent_externally:
    :param email_cc_list:
    :param departure_update_only:
    :return:
    """

    from handling.models import AutoServiceProvisionForm
    auto_spf, auto_spf_created = AutoServiceProvisionForm.objects.update_or_create(
        handling_request=handling_request,
        defaults={
            'sent_to': handling_request.handling_agent,
        }
    )

    # After an amendment, GH needs to be re-confirmed
    # One exception here is if the departure movement is being updated after arrival,
    # in which case we keep handling as confirmed and set a separate flag for this
    if handling_request.opened_gh_amendment_session and departure_update_only:
        action_text = 'Departure Update'
        handling_request.is_awaiting_departure_update_confirmation = True

    elif handling_request.opened_gh_amendment_session:
        action_text = 'Handling Request Amendment'
        handling_request.is_handling_confirmed = False

    else:
        action_text = 'Handling Request'
        handling_request.is_handling_confirmed = False

    if sent_externally:
        # In case if Ground Handling sent externally only add activity_log record
        handling_request.activity_log.create(
            author=author,
            record_slug='sfr_ground_handling_submitted',
            details=f'{action_text}: Sent Externally',
        )
    else:
        # In case if Ground Handling is not sent externally - send email message
        if auto_spf_created or not handling_request.opened_gh_amendment_session:
            generate_auto_spf_email.delay(
                handling_request_id=handling_request.pk,
                requester_person_id=author.pk,
                addresses_cc=email_cc_list,
            )
        else:
            send_ground_handling_spf_amendment_email.delay(
                amendment_session_id=handling_request.opened_gh_amendment_session.pk,
                requester_person_id=author.pk,
                addresses_cc=email_cc_list,
                departure_update_only=departure_update_only
            )

        handling_request.activity_log.create(
            author=author,
            record_slug='sfr_ground_handling_amendment_submitted',
            details=f'{action_text}: Submitted',
        )

    # Close amendment session if it exists
    handling_request.amendment_sessions.filter(
        is_gh_opened=True,
    ).update(is_gh_sent=True, is_gh_opened=False)

    return handling_request
