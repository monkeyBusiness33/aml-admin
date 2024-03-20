// Handler Email Submitting on "Send Handling Request" Dialog
function send_handling_request_form_processing() {
  const id_handler_email_field = $('#id_handler_email')
  const multi_button_2 = $('#multi_button_2')

  if (id_handler_email_field.attr('has_no_primary_email') === 'true' && id_handler_email_field.val() === '') {
    multi_button_2.attr('disabled', true)
  } else {
    multi_button_2.attr('disabled', false)
  }
}

if ($('#send_handling_request_to_handler').length) {
  $("#send_handling_request_to_handler").change(function () {
    send_handling_request_form_processing()
  });
  send_handling_request_form_processing()
}
