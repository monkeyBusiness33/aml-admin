
// Global variables
const request_location_field = $('#id_airport')
const arrivalDateField = $('#id_arrival_date')

function select_created_person(e) {
    $.ajax({
        url: person_callback_url,
        type: 'GET',
        dataType: 'json',
        success: function (res) {
            var newOption = new Option(res.first_name + ' ' + res.last_name, res.id, true, true);
            $('#id_crew').append(newOption).trigger('change');
        }
    });
}

function fleet_created_callback(e) {
}

function organisation_created_callback(e) {
    $.ajax({
        url: created_organisation_callback_url,
        type: 'GET',
        dataType: 'json',
        success: function (res) {
            let newOption = new Option(res.registered_name, res.id, true, true);
            request_location_field.append(newOption).trigger('change');
        }
    });
}

$(document).ready(function () {
    load_modal_buttons()
    // Make Aircraft type disabled until user will be selected
    if ($('#id_crew').select2('data')[0] == 'undefined') {
        $('#id_aircraft_type').attr('disabled', true);
    }
    var asyncSuccessMessage = ' '

    function aircraft_type_pick_trigger(e) {

        if (typeof $('#id_aircraft_type').select2('data')[0] !== "undefined") {
            $('#id_tail_number').attr('disabled', false);
        }
    }

    function client_pick_trigger(e) {
        $('#id_aircraft_type').attr('disabled', false);
        // Disable old event listener on the button if it exists
        $("#create_person_btn").each(function () {
            $(this).modalForm().off()
        });

        $("#tail_number_create_btn").each(function () {
            $(this).modalForm().off()
        });

        // Disable "Add new user" button in case if no url is provided (no permissions)
        if (client_url == '') {
            $("#create_person_btn").attr('disabled', true);
        } else {
            // If url providen process button initialization
            if (typeof $('#client_pick').select2('data')[0] !== "undefined") {
                $("#create_person_btn").attr('disabled', false);
                // Get selected client pk
                client_id = $('#client_pick').select2('data')[0].id
                // Split dummy url to the parts by slash
                client_url_parts = client_url.split('/').slice(0, 6);
                // Change paceholer ID 000 to real unit ID
                client_url_parts[3] = client_id
                // Finalize url
                client_url = client_url_parts.join('/') + '/'

                // Generate Callback URL to get created user to automatically select it
                person_callback_url_parts = person_callback_url.split('/').slice(0, 4);
                person_callback_url_parts[3] = client_id
                person_callback_url = person_callback_url_parts.join('/') + '/'

                // Init modal button
                function clientModalForm() {
                    $("#create_person_btn").each(function () {
                        $(this).modalForm({
                            modalID: "#modal",
                            formURL: client_url,
                            errorClass: ".is-invalid",
                            asyncUpdate: true,
                            asyncSettings: {
                                closeOnSubmit: true,
                                successMessage: asyncSuccessMessage,
                                dataUrl: person_callback_url,
                                dataElementId: "#none",
                                dataKey: "data",
                                addModalFormFunction: clientModalForm,
                                fnPostUpdateRefresh: select_created_person
                            }
                        });
                    });
                }
                clientModalForm();
            }
        }

        if (fleet_create_url == '') {
            $("#tail_number_create_btn").attr('disabled', true);
        } else {
            if (typeof $('#client_pick').select2('data')[0] !== "undefined") {
                // If url providen process button initialization
                $("#tail_number_create_btn").attr('disabled', false);
                // Get selected client pk
                client_id = $('#client_pick').select2('data')[0].id
                // Split dummy url to the parts by slash
                fleet_create_url_parts = fleet_create_url.split('/').slice(0, 5);
                // Change paceholer ID 000 to real unit ID
                fleet_create_url_parts[4] = client_id
                // Finalize url
                fleet_create_url = fleet_create_url_parts.join('/') + '/'

                // Init modal button
                function fleetCreateModalForm() {
                    $("#tail_number_create_btn").each(function () {
                        $(this).modalForm({
                            modalID: "#modal",
                            formURL: fleet_create_url,
                            errorClass: ".is-invalid",
                            asyncUpdate: true,
                            asyncSettings: {
                                closeOnSubmit: true,
                                successMessage: asyncSuccessMessage,
                                dataUrl: ping_url,
                                dataElementId: "#none",
                                dataKey: "data",
                                addModalFormFunction: fleetCreateModalForm,
                                fnPostUpdateRefresh: fleet_created_callback,
                            }
                        });
                    });
                }
                fleetCreateModalForm();
            }
        }

    }

    if (typeof organisation_create_url !== "undefined") {
        function OrganisationCreateModalForm() {
                    $(".organisation_create_btn").each(function () {
                        $(this).modalForm({
                            modalID: "#modal-xl",
                            formURL: organisation_create_url,
                            errorClass: ".is-invalid",
                            asyncUpdate: true,
                            asyncSettings: {
                                closeOnSubmit: true,
                                successMessage: asyncSuccessMessage,
                                dataUrl: created_organisation_callback_url,
                                dataElementId: "#none",
                                dataKey: "data",
                                addModalFormFunction: OrganisationCreateModalForm,
                                fnPostUpdateRefresh: organisation_created_callback,
                            }
                        });
                    });
                }
                OrganisationCreateModalForm();
    }

    $("#create_person_btn").attr('disabled', true);
    $("#tail_number_create_btn").attr('disabled', true);
    $('#client_pick').on('select2:select', client_pick_trigger);
    client_pick_trigger()

     $("#id_tail_number").attr('disabled', true);
     $('#id_aircraft_type').on('select2:select', aircraft_type_pick_trigger);
     aircraft_type_pick_trigger()

    const fuel_required_field = $("#id_fuel_required")
    const fuel_unit_field = $("#id_fuel_unit")
    const fuel_quantity_field = $("#id_fuel_quantity")

    function fuel_required_actions(e) {
         if (typeof fuel_required_field.select2('data')[0] !== "undefined") {
             let fuel_required_field_value = fuel_required_field.select2('data')[0].id
             if (fuel_required_field_value === 'NO_FUEL') {

                 fuel_unit_field.val(null).change()
                 fuel_unit_field.attr('required', false)
                 fuel_unit_field.attr('disabled', true)

                 fuel_quantity_field.val(null)
                 fuel_quantity_field.attr('required', false)
                 fuel_quantity_field.attr('disabled', true)
             } else {
                 fuel_unit_field.attr('disabled', false)
                 fuel_unit_field.attr('required', true)

                 fuel_quantity_field.attr('disabled', false)
                 fuel_quantity_field.attr('required', true)
             }
         }

    }

    fuel_required_field.change(function () {
        fuel_required_actions()
    });


    function arrival_passengers_actions() {
        let arrival_is_passengers_onboard_checked = arrival_is_passengers_onboard_field.is(':checked')
        let arrival_is_passengers_tbc_checked = arrival_is_passengers_tbc_field.is(':checked')

        if (!arrival_is_passengers_onboard_checked) {
            arrival_is_passengers_tbc_field.prop('checked', false)
            arrival_is_passengers_tbc_field.attr('disabled', true)
            arrival_passengers_field.val(null)
            arrival_passengers_field.attr('disabled', true)
        } else {
            arrival_is_passengers_tbc_field.attr('disabled', false)
            arrival_passengers_field.attr('disabled', false)

            if (arrival_is_passengers_tbc_checked) {
                arrival_passengers_field.val(null)
                arrival_passengers_field.attr('disabled', true)
            } else {
                arrival_passengers_field.attr('disabled', false)
            }
        }

    }

    function departure_passengers_actions() {
        let departure_is_passengers_onboard_checked = departure_is_passengers_onboard_field.is(':checked')
        let departure_is_passengers_tbc_checked = departure_is_passengers_tbc_field.is(':checked')

        if (!departure_is_passengers_onboard_checked) {
            departure_is_passengers_tbc_field.prop('checked', false)
            departure_is_passengers_tbc_field.attr('disabled', true)
            departure_passengers_field.val(null)
            departure_passengers_field.attr('disabled', true)
        } else {
            departure_is_passengers_tbc_field.attr('disabled', false)
            departure_passengers_field.attr('disabled', false)

            if (departure_is_passengers_tbc_checked) {
                departure_passengers_field.val(null)
                departure_passengers_field.attr('disabled', true)
            } else {
                departure_passengers_field.attr('disabled', false)
            }
        }

    }

    function movement_timezone() {
        // Disable timezone fields in case if location have no lat/lon in the database
        if (typeof request_location_field.select2('data')[0] !== "undefined") {
            let is_lat_lon_available = request_location_field.select2('data')[0].is_lat_lon_available
            if (typeof is_lat_lon_available !== "undefined") {
                if (!is_lat_lon_available) {
                    arrival_is_local_timezone_field.val('False').change()
                    departure_is_local_timezone.val('False').change()
                }
                arrival_is_local_timezone_field.prop('disabled', !is_lat_lon_available)
                departure_is_local_timezone.prop('disabled', !is_lat_lon_available)
            }
        }
    }

    // Airport Field
    const request_location_field = $('#id_airport')

    const handling_agent_field = $('#id_handling_agent')

    const arrival_is_local_timezone_field = $('#id_arrival_is_local_timezone')
    const departure_is_local_timezone = $('#id_departure_is_local_timezone')

    const arrival_is_passengers_onboard_field = $('#id_arrival_is_passengers_onboard')
    const arrival_is_passengers_tbc_field = $('#id_arrival_is_passengers_tbc')
    const arrival_passengers_field = $('#id_arrival_passengers')

    const departure_is_passengers_onboard_field = $('#id_departure_is_passengers_onboard')
    const departure_is_passengers_tbc_field = $('#id_departure_is_passengers_tbc')
    const departure_passengers_field = $('#id_departure_passengers')

    // Disable Handling Agent field by default
    handling_agent_field.prop('disabled', true)

    // Conditionally enable Handling Agent Field on Location selection
    function get_preferred_handler_ajax(e) {
        $.ajax({
            url: get_preferred_handler_url,
            type: 'GET',
            dataType: 'json',
            success: function (res) {
                let newOption = new Option(res.registered_name, res.id, true, true);
                handling_agent_field.append(newOption).trigger('change');
            }
        });
    }

    request_location_field.change(function () {
        if (typeof request_location_field.select2('data')[0] !== "undefined") {
            if (handling_agent_field.length) {
                handling_agent_field.prop('disabled', false)

                let selected_location_id = request_location_field.select2('data')[0].id
                let get_preferred_handler_url_parts = get_preferred_handler_url.split('/').slice(0, 5);
                // Change placeholder ID 000 to real unit ID
                get_preferred_handler_url_parts[4] = selected_location_id
                // Finalize url
                get_preferred_handler_url = get_preferred_handler_url_parts.join('/') + '/'
                get_preferred_handler_ajax()
            }

        } else {
            handling_agent_field.prop('disabled', true)
        }
    });

    $('#create_handling_reqeust').change(function () {
        arrival_passengers_actions()
        departure_passengers_actions()
    });

    request_location_field.change(function () {
        movement_timezone()
    });

    movement_timezone()
    arrival_passengers_actions()
    departure_passengers_actions()


  arrivalDateField.change(function () {
    let dateNow = new Date().setHours(0, 0, 0, 0);
    let arrivalDateValObj = Date.parse(arrivalDateField.val())

    if (arrivalDateValObj < dateNow) {
      swalWithBootstrapButtons.fire({
        icon: 'question',
        title: 'Create Retrospective S&F Request?',
        html: 'The movement date(s) are in past, please confirm you wish to create retrospective S&F Request. <br><br>' +
          'You will have <b>5 minutes</b> to submit all details to promote S&F Request to "COMPLETED" status, otherwise it will become "EXPIRED"',
        showCancelButton: true,
        confirmButtonText: "Create",
        cancelButtonText: 'Cancel',
        reverseButtons: true,
        // Close Flatpickr calendar after confirmation
        didClose: () => document.querySelector("#id_arrival_date").parentNode._flatpickr.close()
      }).then(function (result) {

        if (result.value) {
        } else {
          $('#id_arrival_date').next('.input').val(null)
        }

      });
    }
  });

});

window.djangoFlatpickrOptions_arrival_date = {
    onChange: function (selectedDates) {
      document.querySelector("#id_departure_date").parentNode._flatpickr.config.minDate=selectedDates[0]
      document.querySelector("#id_departure_date").parentNode._flatpickr.clear()

    }
}
