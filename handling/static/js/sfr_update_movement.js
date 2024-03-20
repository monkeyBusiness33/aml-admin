// S&F Request Update Movement Passengers
function passengers_actions() {
  let is_passengers_onboard_checked = is_passengers_onboard_field.is(':checked')
  let is_passengers_tbc_checked = is_passengers_tbc_field.is(':checked')

  if (!is_passengers_onboard_checked) {
    is_passengers_tbc_field.prop('checked', false)
    is_passengers_tbc_field.attr('disabled', true)
    passengers_field.val(null)
    passengers_field.attr('disabled', true)
  } else {
    is_passengers_tbc_field.attr('disabled', false)
    passengers_field.attr('disabled', false)

    if (is_passengers_tbc_checked) {
      passengers_field.val(null)
      passengers_field.attr('disabled', true)
    } else {
      passengers_field.attr('disabled', false)
    }
  }

}

const sfr_update_movement_form = $('#sfr_update_movement')
const is_passengers_onboard_field = $('#id_is_passengers_onboard')
const is_passengers_tbc_field = $('#id_is_passengers_tbc')
const passengers_field = $('#id_passengers')

sfr_update_movement_form.change(function () {
  passengers_actions()
});
sfr_update_movement_form.ready(function () {
  passengers_actions()
});
