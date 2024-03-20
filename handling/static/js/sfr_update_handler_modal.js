$(document).ready(function () {
    const handling_request_handler_form = $('#handling_request_handler_form')
    const gh_cancellation_form = $('#gh_cancellation_form')
    const handling_agent_field = $('#id_handling_agent')

    function ground_handler_selection_processing() {
        if (typeof handling_agent_field.select2('data')[0] !== "undefined") {
            let selected_ground_handler = handling_agent_field.select2('data')[0].id

            if (selected_ground_handler !== ground_handler_confirmed_for) {
                gh_cancellation_form.removeClass('d-none')
            } else {
                gh_cancellation_form.addClass('d-none')
            }
        }
    }

    handling_request_handler_form.change(function () {
        if (ground_handler_confirmed_for !== ' ') {
            ground_handler_selection_processing()
        }
    });

    if (ground_handler_confirmed_for !== ' ') {
        ground_handler_selection_processing()
    }

})