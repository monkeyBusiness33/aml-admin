// Handling Reqeust "Update Tail Number" dialog

var tailNumberField = $("#id_tail_number")

if ($('#update_tail_number_form').length) {
  $("#id_unassign_tail").change(function () {
    var unassign_tail = $("#id_unassign_tail").is(':checked')

    if (unassign_tail) {
      tailNumberField.val(null).trigger('change');
      tailNumberField.prop("disabled", true);
    } else {
      tailNumberField.prop("disabled", false);
    }
  });
}
