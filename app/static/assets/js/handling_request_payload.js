$('#passengers_payload_section .formset-row').slice(0, handling_request_passengers).each(function (i, obj) {
    let removeButton = $(obj).find('.formset_row_del_btn')
    $(removeButton).prop('disabled', true);
    $(removeButton).data('persistent', true);
});

passengers_payload_section = $("#passengers_payload_section")
cargo_payload_section = $("#cargo_payload_section")

function gender_select_trigger(field) {
    if (typeof field.select2('data')[0] !== "undefined") {
        let weight_field = field.closest('tr').find('.passenger-weight-value')
        if (field.select2('data')[0].id === '1') {
            weight_field.val(pax_weight_male)
        }
        if (field.select2('data')[0].id === '2') {
            weight_field.val(pax_weight_female)
        }
    }
}

$(".gender-select").change(function () {
    gender_select_trigger($(this))
});


function calculate_payload() {
    let arrival_weight = 0
    let departure_weight = 0

    // Passengers weight calculation
    $("#passengers_payload_section .formset-row:not(.d-none,.to_delete)").each(function () {
        let passenger_weight_field = $(this).closest('tr').find('.passenger-weight-value')
        let passenger_gender_field = $(this).closest('tr').find('.gender-select.select2-hidden-accessible')
        let is_arrival_checkbox = $(this).closest('tr').find('.is-arrival-checkbox')
        let is_departure_checkbox = $(this).closest('tr').find('.is-departure-checkbox')

        if (typeof passenger_gender_field.select2('data') !== "undefined" && typeof passenger_gender_field.select2('data')[0] !== "undefined") {
            if (is_arrival_checkbox.prop('checked') === true) {
                arrival_weight += Number(passenger_weight_field.val());
            }
            if (is_departure_checkbox.prop('checked') === true) {
                departure_weight += Number(passenger_weight_field.val());
            }
        }

    });

    // Cargo weight calculation
    $("#cargo_payload_section .formset-row:not(.d-none,.to_delete)").each(function() {
        let cargo_weight = $(this).closest('tr').find('.cargo-weight')
        let cargo_quantity = $(this).closest('tr').find('.cargo-quantity')
        let is_arrival_checkbox = $(this).closest('tr').find('.is-arrival-checkbox')
        let is_departure_checkbox = $(this).closest('tr').find('.is-departure-checkbox')

        if (is_arrival_checkbox.prop('checked') === true) {
            let total_weight =  Number(cargo_weight.val()) *  Number(cargo_quantity.val());
            arrival_weight += total_weight
        }
        if (is_departure_checkbox.prop('checked') === true) {
            let total_weight =  Number(cargo_weight.val()) *  Number(cargo_quantity.val());
            departure_weight += total_weight
        }

    })
    $("#payload_total_value").html(arrival_weight + ' lbs  /  ' +  departure_weight + ' lbs')
}


function identifier_trigger() {
    $('#passengers_payload_section .formset-row:not(.d-none,.to_delete)').each(function (index) {
        let identifier = index + 1
        let row_gender_field = $(this).find('.gender-select.select2-hidden-accessible')
        let identifier_field = $(this).find('.passenger-identifier')
        let identifier_value = $(this).find('.passenger-identifier-value')

        if (typeof row_gender_field.select2('data') !== "undefined" && typeof row_gender_field.select2('data')[0] !== "undefined") {
            if (!identifier_field.val()) {
                identifier_field.val(identifier)
                identifier_value.html(identifier)
            }
        }

    })
}

$(document).ready(function () {
    calculate_payload();
})
passengers_payload_section.change(function () {
    identifier_trigger()
});

$('form').click(function () {
    calculate_payload()
});
