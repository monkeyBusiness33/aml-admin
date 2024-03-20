// fuel_index_pricing_modal.js

function valid_ufn_trigger() {
  validToField = $("#id_valid_to");
  validToFieldLabel = $("label[for='" + validToField.attr('id') + "']");
  validUFNChecked = $("#id_valid_ufn").is(':checked')
  if (validUFNChecked) {
    validToField.val(null).trigger('change')
    validToField.prop('disabled', true)
    validToField.prop('required', false)
    validToFieldLabel.removeClass('required');
  } else {
    validToField.prop('disabled', false)
    validToField.prop('required', true)
    validToFieldLabel.addClass('required');
  }
}

function src_org_trigger() {
  srcDocField = $("#id_source_document");
  srcOrgSelected = $("#id_source_organisation").val() != null;

  if (srcOrgSelected) {
    srcDocField.prop('disabled', false);
  } else {
    srcDocField.prop('disabled', true);
  }
}

$("#id_valid_ufn").change(function () {
  valid_ufn_trigger();
});

$("#id_source_organisation").change(function () {
  src_org_trigger();
});

valid_ufn_trigger()
src_org_trigger()
