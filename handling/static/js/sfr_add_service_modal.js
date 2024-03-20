// Handling Request "Add Service" dialog
if ($('#add_services_to_handling_request').length) {
  $("#id_booking_quantity").hide()
  $('label[for=id_booking_quantity]').hide()
  $("#id_booking_text").hide();
  $('label[for=id_booking_text]').hide()

  $("#id_service").change(function () {
    var serviceField = $('#id_service')
    var quantity_selection_uom = serviceField.select2('data')[0].quantity_selection_uom
    var is_allowed_free_text = serviceField.select2('data')[0].is_allowed_free_text
    var is_allowed_quantity_selection = serviceField.select2('data')[0].is_allowed_quantity_selection

    var bookingTextField = $("#id_booking_text")
    var bookingTextLabel = $('label[for=id_booking_text]')
    var bookingQtyField = $("#id_booking_quantity")
    var bookingQtyLabel = $('label[for=id_booking_quantity]')


    if (is_allowed_free_text) {
      bookingTextField.show();
      bookingTextField.prop('required', true);
      bookingTextLabel.show()
      bookingTextLabel.addClass('required')
    } else {
      bookingTextField.hide();
      bookingTextField.prop('required', false);
      bookingTextLabel.hide()
      bookingTextLabel.removeClass('required')
    }

    if (is_allowed_quantity_selection) {
      var label_text = bookingQtyLabel.html()
      bookingQtyLabel.html(label_text + ' (' + quantity_selection_uom + ')')

      bookingQtyField.show();
      bookingQtyLabel.show()

      bookingQtyLabel.addClass('required')
      bookingQtyField.prop('required', true);
    } else {
      bookingQtyField.hide();
      bookingQtyLabel.hide()
      bookingQtyField.prop('required', false);
    }

  });
}
