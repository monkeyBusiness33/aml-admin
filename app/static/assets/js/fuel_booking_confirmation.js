$(document).ready(function () {

    function id_dla_contracted_fuel_processing() {
        const id_dla_contracted_fuel_checkbox = $("#id_dla_contracted_fuel")
        let dla_contracted_fuel = id_dla_contracted_fuel_checkbox.is(':checked')
        let is_dla_contracted_fuel_disabled = id_dla_contracted_fuel_checkbox.is(':disabled')

        if (!is_dla_contracted_fuel_disabled) {
            if (dla_contracted_fuel) {
                $("#id_fuel_order_number").val(null).prop("disabled", true).prop('required', false);
                $("#id_fuel_release").val(null).prop("disabled", true).prop('required', false);
            } else {
                $("#id_fuel_order_number").prop("disabled", false)
                $("#id_fuel_release").prop("disabled", false)
            }
        }
    }

    function fuel_booking_amendment_processing() {
        const fuel_required = $("#id_fuel_required")
        const fuel_quantity = $("#id_fuel_quantity")
        const fuel_unit = $("#id_fuel_unit")
        const fuel_prist_required = $("#id_fuel_prist_required")
        if (typeof fuel_required.select2('data')[0] !== "undefined") {
            let fuel_required_value = fuel_required.select2('data')[0].id

            if (fuel_required_value === 'NO_FUEL') {
                fuel_quantity.val(null)
                fuel_quantity.attr('disabled', true)
                fuel_unit.val(null)
                fuel_unit.attr('disabled', true)
                fuel_prist_required.prop('checked', false);
                fuel_prist_required.attr('disabled', true)
            } else {
                fuel_quantity.attr('disabled', false)
                fuel_unit.attr('disabled', false)
                fuel_prist_required.attr('disabled', false)
            }
        }
    }

    if ($('#fuel_booking_confirmation').length) {
        const fuel_required = $("#id_fuel_required")

        $("#id_dla_contracted_fuel").change(function () {
            id_dla_contracted_fuel_processing()
        });

        fuel_required.change(function () {
            fuel_booking_amendment_processing()
        });

        id_dla_contracted_fuel_processing()
        fuel_booking_amendment_processing()
    }

});