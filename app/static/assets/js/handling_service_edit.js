$('#handling_service_edit').ready(function () {

    // function id_is_dla_fields_func() {
    //     var checked = $('#id_is_dla').prop('checked');
    //     if (checked) {
    //         $('#id_availability').prop('disabled', true);
    //         $('#id_availability').val(null).change();
    //
    //         $('#id_is_dla_visible_arrival').prop('disabled', false);
    //         $('#id_is_dla_visible_departure').prop('disabled', false);
    //         $('#id_is_spf_visible').prop('disabled', false);
    //     } else {
    //         $('#id_availability').prop('disabled', false);
    //         $('#id_is_dla_visible_arrival').prop('checked', false).prop('disabled', true);
    //         $('#id_is_dla_visible_departure').prop('checked', false).prop('disabled', true);
    //         $('#id_is_spf_visible').prop('checked', false).prop('disabled', true);
    //     }
    // }
    //
    // id_is_dla_fields_func()
    // $('#id_is_dla').change(id_is_dla_fields_func)

    function service_free_text_quantity_trigger() {
        var is_allowed_free_text = $("#id_is_allowed_free_text").is(':checked')
        var is_allowed_quantity_selection = $("#id_is_allowed_quantity_selection").is(':checked')

        if (is_allowed_free_text) {
            $("#id_is_allowed_quantity_selection").prop('disabled', true);
        } else {
            $("#id_is_allowed_quantity_selection").prop('disabled', false);
        }

        if (is_allowed_quantity_selection) {
            $("#id_is_allowed_free_text").prop('disabled', true);
            $("#id_quantity_selection_uom").prop('disabled', false);
        } else {
            $("#id_is_allowed_free_text").prop('disabled', false);

            $('#id_quantity_selection_uom').val(null);
            $('#id_quantity_selection_uom').trigger('change');
            $("#id_quantity_selection_uom").prop('disabled', true);
        }

    }
    $('#id_is_allowed_free_text').change(service_free_text_quantity_trigger)
    $('#id_is_allowed_quantity_selection').change(service_free_text_quantity_trigger)
    service_free_text_quantity_trigger()



});
