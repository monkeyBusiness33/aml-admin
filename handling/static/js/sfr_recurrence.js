recurrenceArrivalDateDatePickerElement = document.getElementById('update_recurrence_arrival_datepicker');
if (recurrenceArrivalDateDatePickerElement) {
    recurrenceArrivalDateDatePicker = new Datepicker(recurrenceArrivalDateDatePickerElement, {
        buttonClass: 'btn',
        format: 'yyyy-mm-dd',
        autohide: true,
        minDate: new Date(),
    });
}

recurrenceDepartureDateDatePickerElement = document.getElementById('update_recurrence_departure_datepicker');
if (recurrenceDepartureDateDatePickerElement) {
    recurrenceDepartureDateDatePicker = new Datepicker(recurrenceDepartureDateDatePickerElement, {
        buttonClass: 'btn',
        format: 'yyyy-mm-dd',
        autohide: true,
        minDate: new Date(),
    });
}

recurrenceFinalDateDatePicker = new Datepicker(document.getElementById('id_final_recurrence_date'), {
    buttonClass: 'btn',
    format: 'yyyy-mm-dd',
    autohide: true,
    minDate: new Date(),
});

recurrenceSpecificDatesDatePicker = new Datepicker(document.getElementById('id_specific_recurrence_dates'), {
    buttonClass: 'btn',
    format: 'yyyy-mm-dd',
    autohide: false,
    minDate: new Date(),
    maxNumberOfDates: 30,
});

if (typeof is_update_recurrence_modal === 'undefined') {
    is_update_recurrence_modal = false

}

recurrence_section = $('#recurrence_section')
recurrence_details_section = $('#recurrence_details_section')
enable_recurrence = $('#id_enable_recurrence')
specific_recurrence_dates_field = $('#id_specific_recurrence_dates')
operating_days_field = $('input[name="operating_days"]')
final_recurrence_date_field = $('#id_final_recurrence_date')
weeks_of_recurrence_field = $('#id_weeks_of_recurrence')
arrival_date_field = $('#id_arrival_date')


function enable_input_field(field, value) {
    let enable_recurrence_checked = enable_recurrence.is(':checked')

    field.attr("disabled", !value);
    field.attr("required", value);
    let label = $('label[for="' + field.attr('id') + '"]')
    if (value) {
        label.addClass('required')
    } else {
        label.removeClass('required')
        field.val(null)
    }

    if (!enable_recurrence_checked && !is_update_recurrence_modal ) {
        field.attr("required", false);
        label.removeClass('required')
        field.val(null)
    }
}

function enable_operating_days_field(value) {
    $("input[name='operating_days']").each(function () {
        $(this).attr("disabled", !value);
        if (!value) {
            $(this).prop('checked', false)
        }

    });
}

function show_recurrence_details_section(value) {
    if (value || is_update_recurrence_modal) {
        recurrence_details_section.removeClass('d-none')
    } else {
        recurrence_details_section.addClass('d-none')
    }
}

function recurrence_section_change() {
    let enable_recurrence_checked = enable_recurrence.is(':checked')
    if (!is_update_recurrence_modal) {
        enable_input_field(specific_recurrence_dates_field, enable_recurrence_checked)
        enable_operating_days_field(enable_recurrence_checked)
        enable_input_field(final_recurrence_date_field, enable_recurrence_checked)
        enable_input_field(weeks_of_recurrence_field, enable_recurrence_checked)

        show_recurrence_details_section(enable_recurrence_checked)
    }

}

function specific_recurrence_date_change() {
    let specific_recurrence_dates_value = specific_recurrence_dates_field.val()
    let specific_recurrence_dates_value_bool = (specific_recurrence_dates_value !== '');
    enable_operating_days_field(!specific_recurrence_dates_value_bool)
    enable_input_field(final_recurrence_date_field, !specific_recurrence_dates_value_bool)
    enable_input_field(weeks_of_recurrence_field, !specific_recurrence_dates_value_bool)
}

function operating_days_change() {
    let operating_days_checked = $('input[name="operating_days"]:checked').length;
    let operating_days_value_bool = (operating_days_checked > 0);
    enable_input_field(specific_recurrence_dates_field, !operating_days_value_bool)

    enable_input_field(final_recurrence_date_field, operating_days_value_bool)
    enable_input_field(weeks_of_recurrence_field, operating_days_value_bool)

    if (final_recurrence_date_field.val() !== '') {
        enable_input_field(weeks_of_recurrence_field, !operating_days_value_bool)
    }

    if (weeks_of_recurrence_field.val() !== '') {
        enable_input_field(final_recurrence_date_field, !operating_days_value_bool)
    }
}

function final_recurrence_date_change() {
    let final_recurrence_date_field_value_bool = (final_recurrence_date_field.val() !== '');
    enable_input_field(weeks_of_recurrence_field, !final_recurrence_date_field_value_bool)
}

function weeks_of_recurrence_change() {
    let weeks_of_recurrence_field_value_bool = (weeks_of_recurrence_field.val() !== '');
    enable_input_field(final_recurrence_date_field, !weeks_of_recurrence_field_value_bool)
}

operating_days_field.change(function () {
    operating_days_change()
});

enable_recurrence.change(function () {
    recurrence_section_change()
    operating_days_change()
});

specific_recurrence_dates_field.on("changeDate", function(e, obj) {
    specific_recurrence_date_change()
});

final_recurrence_date_field.on("changeDate", function(e, obj) {
    final_recurrence_date_change()
});

weeks_of_recurrence_field.change(function () {
    weeks_of_recurrence_change()
});

arrival_date_field.on("changeDate", function(e, obj) {
    recurrenceFinalDateDatePicker.setOptions({minDate: new Date(arrival_date_field.val())})
    recurrenceSpecificDatesDatePicker.setOptions({minDate: new Date(arrival_date_field.val())})
});

recurrence_section_change()
specific_recurrence_date_change()
operating_days_change()

// weeks_of_recurrence_field validation
document.getElementById('id_weeks_of_recurrence').addEventListener('keyup', function(){
    this.value = (parseInt(this.value) < 1 || parseInt(this.value) > 54 || isNaN(this.value)) ? "" : (this.value)
});

// S&F Request Recurrence cancellation confirmation
$(document).on('click', '#cancel_recurrence_requests_btn', function (e) {
    swalWithBootstrapButtons.fire({
        icon: 'error',
        title: 'Cancel S&F Request Recurrence Sequence?',
        text: 'This action will cancel all S&F Requests that is not completed yet in current recurrence sequence.',
        showCancelButton: true,
        confirmButtonText: "Yes, cancel it!",
        cancelButtonText: 'No, go back!',
    }).then(function (result) {
        if (result.value) {
            swalWithBootstrapButtons.fire(
                'Cancelled',
                'The event has been deleted.',
                'success'
            );
            $.ajax({
                type: 'POST',
                url: cancel_recurrence_url,
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'sessionid': getCookie('sessionid')
                },
                success: function (response) {
                    if (response.success === 'true') {
                        location.reload();
                    }
                },
            });
        } else if (result.dismiss === Swal.DismissReason.cancel) {
        }
    })
});
