// fuel_agreement_void_modal.js

function void_immediately_trigger(e) {
  endDateField = $("#id_end_date");
  endDateFieldLabel = $("label[for='" + endDateField.attr('id') + "']");
  voidImmediatelyChecked = $("#id_void_immediately").is(':checked')
  if (voidImmediatelyChecked) {
    endDateField.val(null).trigger('change')
    endDateField.prop('disabled', true)
    endDateField.prop('required', false)
    endDateFieldLabel.removeClass('required');
  } else {
    endDateField.prop('disabled', false)
    endDateField.prop('required', true)
    endDateFieldLabel.addClass('required');
  }
}

$("#id_void_immediately").change(function () {
  void_immediately_trigger()
});

void_immediately_trigger()
