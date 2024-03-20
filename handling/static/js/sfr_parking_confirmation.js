// S&F Request Parking confirmation dialog processing
const booking_confirmation_form = $('#booking_confirmation')
const parking_apron_field = $('#id_parking_apron')
const parking_apron_label = $("label[for='id_parking_apron']")
const parking_stand_field = $('#id_parking_stand')
const id_parking_confirmed_on_day_of_arrival_field = $('#id_parking_confirmed_on_day_of_arrival')

function parking_confirmation_form_processing() {
  console.log('asdas')
  if (id_parking_confirmed_on_day_of_arrival_field.is(':checked')) {
    parking_apron_field.prop('required', false)
    parking_apron_label.removeClass('required')
    parking_apron_field.val(null)
    parking_apron_field.prop('disabled', true)

    parking_stand_field.prop('disabled', true)
    parking_stand_field.val(null)
  } else {
    parking_apron_field.prop('required', true)
    parking_apron_label.addClass('required')
    parking_apron_field.prop('disabled', false)
    parking_stand_field.prop('disabled', false)
  }
}

if (booking_confirmation_form.length) {
  booking_confirmation_form.change(function () {
    parking_confirmation_form_processing()
  });
  parking_confirmation_form_processing()
}
