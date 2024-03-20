var tailNumberField = $('#id_tail_number')
var registrationField = $('#id_registration')
var registrationFieldLabel = $('label[for=id_registration]')
var aircraftTypeField = $('id_type')
var aircraftTypeFieldLabel = $('label[for=id_type]')

function showAircraftCreateForm(value) {

  if (value === true) {
    $('#create_aircraft').removeClass("d-none");
    tailNumberField.prop('disabled', true)
    tailNumberField.val(null)
    tailNumberField.change()

    // Field attrs
    registrationField.attr('required', true)
    registrationFieldLabel.addClass('required')
    aircraftTypeField.attr('required', true)
    aircraftTypeFieldLabel.addClass('required')

  } else {
    $('#create_aircraft').addClass("d-none");
    tailNumberField.prop('disabled', false)

    // Field attrs
    registrationField.attr('required', false)
    registrationFieldLabel.removeClass('required')
    aircraftTypeField.attr('required', false)
    aircraftTypeFieldLabel.removeClass('required')

  }

}

$(document).ready(function () {
  $('#tail_number_create_btn').click(function () {
    if ($('#create_aircraft:visible').length) {
      showAircraftCreateForm(false)
    } else {
      showAircraftCreateForm(true)
    }
  })
})
