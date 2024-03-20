function operator_preferred_ground_handler_form_processing() {
  if (typeof operator_preferred_handler_location_field.select2('data')[0] !== "undefined") {
    operator_preferred_handler_ground_handler_field.prop('disabled', false)
  }
}

const operator_preferred_ground_handler_form = $('#operator_preferred_ground_handler_form')
const operator_preferred_handler_location_field = $('#id_location')
const operator_preferred_handler_ground_handler_field = $('#id_ground_handler')

if (operator_preferred_ground_handler_form.length) {
  operator_preferred_handler_ground_handler_field.prop('disabled', true)
  operator_preferred_ground_handler_form.change(function () {
    operator_preferred_ground_handler_form_processing()
  });
  operator_preferred_ground_handler_form_processing()
}
