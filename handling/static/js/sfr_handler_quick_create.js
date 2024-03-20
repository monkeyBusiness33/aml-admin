// Handling Request Handler (HandlingAgent) form
function handling_request_handler_create_actions(disable_details = true) {
  const contact_email_field = $("#id_contact_email_quick_create")
  const contact_email_label = $("label[for='id_contact_email_quick_create']")

  const contact_phone_field = $("#id_contact_phone")
  const contact_phone_label = $("label[for='id_contact_phone']")

  const ops_frequency_field = $("#id_ops_frequency")
  const ops_frequency_label = $("label[for='id_ops_frequency']")

  if (disable_details) {
    $('#handler_quick_create_info').addClass('d-none')
    // Disable Handler Details fields
    contact_email_field.attr('required', false)
    contact_email_field.addClass('d-none')
    contact_email_label.addClass('d-none')
    contact_email_label.removeClass('required')

    contact_phone_field.addClass('d-none')
    contact_phone_label.addClass('d-none')

    ops_frequency_field.addClass('d-none')
    ops_frequency_label.addClass('d-none')

  } else {
    $('#handler_quick_create_info').removeClass('d-none')
    // Enable Handler Details fields
    contact_email_field.attr('required', true)
    contact_email_field.removeClass('d-none')
    contact_email_label.removeClass('d-none')
    contact_email_label.addClass('required')

    contact_phone_field.removeClass('d-none')
    contact_phone_label.removeClass('d-none')

    ops_frequency_field.removeClass('d-none')
    ops_frequency_label.removeClass('d-none')
  }
}

if ($('#id_contact_email_quick_create').length) {

  // Append information section for additional fields
  let handler_quick_create_info = '<div id="handler_quick_create_info" class="alert alert-primary" role="alert">\n' +
    '<i class="fas fa-exclamation-triangle me-3"></i>  Please submit details for new Handler organisation\n' +
    '</div>'

  $(handler_quick_create_info).insertBefore("label[for='id_contact_email_quick_create']");

  handling_request_handler_create_actions()
  const handling_agent_field = $("#id_handling_agent")

  handling_agent_field.change(function () {
    if (typeof handling_agent_field.select2('data')[0] !== "undefined") {

      // In case of input non-existent handler name we should display details fields to fill by user
      if (handling_agent_field.select2('data')[0].element.dataset.select2Tag === 'true') {
        handling_request_handler_create_actions(false)
      } else {
        handling_request_handler_create_actions(true)
      }
    }
  });
}
