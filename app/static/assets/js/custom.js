
function load_modal_buttons(e) {
    $(".modal_button_validation").each(function () {
        $(this).off('click')
        $(this).modalForm({
            formURL: $(this).data('form-url'),
            errorClass: ".is-invalid",
            modalID: $(this).data('modal') || '#modal',
        });
    });

    $(".modal_button_novalidation").each(function () {
        $(this).off('click')
        $(this).modalForm({
            formURL: $(this).data('form-url'),
            errorClass: ".is-invalid",
            modalID: $(this).data('modal') || '#modal',
            isDeleteForm: true
        });
    });
}
load_modal_buttons()

// Enable tooltips
function load_tooltips(e) {
  let tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
  })
}
load_tooltips()

// Enable popovers
function load_popovers() {
  let popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
  popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl)
  })
}
load_popovers()


function sidebar_collapse() {
  document.getElementById('sidebarMenu').classList.add('contracted');
  window.sidebarTemporaryContracted = true;
}


$(document).ready(function () {
    if ($('body .django-select2').length) {
        setTimeout(() => {
            $('body .django-select2').djangoSelect2({
                dropdownParent: $('body'),
                width: '100%'
            });

        }, 150);
    }

    // "Add Another Address" button on Aircraft Operator page
    function address_form_delete_button_state() {
        var remainForms = $('.address_form:not(.to_delete,.d-none)').length
        if (remainForms === 1) {
            var btn = $('.address_form:not(.to_delete,.d-none)').find('.del_organisation_address_btn')
            $(btn).prop('disabled', true);
        } else {
            var btn = $('.del_organisation_address_btn').each(function (index, value) {
                $(this).prop('disabled', false);
            });
        }
    }
    address_form_delete_button_state()

    $("#add_another_address_btn").click(function () {
        $(".address_form.d-none:not(.to_delete)").first().removeClass("d-none");
        var remainForms = $('.address_form.d-none:not(.to_delete)').length
        if (remainForms === 0) {
            $(this).prop('disabled', true);
        }
        address_form_delete_button_state()
    });

    $(".del_organisation_address_btn").click(function () {
        var addressFormPrefix = $(this).attr('data-address-form-pre')
        $('#id_' + addressFormPrefix + '-DELETE').prop('checked', true);
        $("#id_" + addressFormPrefix + '_card').first().addClass("d-none to_delete");
        address_form_delete_button_state()
    });

    // "Person Positions" on Person Create/Edit page
    function person_positions_form_delete_button_state() {
        var remainForms = $('.person_positions_form:not(.to_delete,.d-none)').length
        if (remainForms === 1) {
            var btn = $('.person_positions_form:not(.to_delete,.d-none)').find('.del_person_position_btn')
            $(btn).prop('disabled', true);
        } else {
            var btn = $('.del_person_position_btn').each(function (index, value) {
                $(this).prop('disabled', false);
            });
        }
    }
    person_positions_form_delete_button_state()

    $("#add_person_position_btn").click(function () {
        $(".person_positions_form.d-none:not(.to_delete)").first().removeClass("d-none");
        var remainForms = $('.person_positions_form.d-none:not(.to_delete)').length
        if (remainForms === 0) {
            $(this).prop('disabled', true);
        }
        person_positions_form_delete_button_state()
    });

    $(".del_person_position_btn").click(function () {
        var positionFormPrefix = $(this).attr('data-form-pre')
        $('#id_' + positionFormPrefix + '-DELETE').prop('checked', true);
        $("#id_" + positionFormPrefix + '_card').first().addClass("d-none to_delete");
        person_positions_form_delete_button_state()
    });

    // "Into-Plane Agent Locations" on IPA Create/Edit page
    function ipa_locations_form_delete_button_state() {
        var remainForms = $('.ipa_locations_form:not(.to_delete,.d-none)').length
        if (remainForms === 1) {
            var btn = $('.ipa_locations_form:not(.to_delete,.d-none)').find('.del_ipa_locations_btn')
            $(btn).prop('disabled', true);
        } else {
            var btn = $('.del_ipa_locations_btn').each(function (index, value) {
                $(this).prop('disabled', false);
            });
        }
    }
    ipa_locations_form_delete_button_state()

    $("#add_ipa_locations_btn").click(function () {
        $(".ipa_locations_form.d-none:not(.to_delete)").slice(0, 5).removeClass("d-none");
        var remainForms = $('.ipa_locations_form.d-none:not(.to_delete)').length
        if (remainForms === 0) {
            $(this).prop('disabled', true);
        }
        ipa_locations_form_delete_button_state()
    });

    $(".del_ipa_locations_btn").click(function () {
        var FormPrefix = $(this).attr('data-form-pre')
        $('#id_' + FormPrefix + '-DELETE').prop('checked', true);
        $("#id_" + FormPrefix + '_card').first().addClass("d-none to_delete");
        ipa_locations_form_delete_button_state()
    });

    // Highlight required fields by red border on form submission
    $("button[type='submit']").click(function () {
        $('form').each(function () {
            $(':input[required]:visible').each(function () {
                if (!($(this).val())) {
                    $(this).addClass('is-invalid');
                    isError = true;
                } else
                    $(this).removeClass('is-invalid');
            });

            $('.django-select2[required]').each(function () {
                if (!($(this).val())) {
                    $(this).next().find('.select2-selection').addClass('has-error form-control is-invalid');;
                } else
                    $(this).removeClass('is-invalid');
            });

        });

    });

    // Organisation name duplicate finder
    if ($('#id_organisation_details_form_pre-registered_name').length) {
        $("#id_organisation_details_form_pre-registered_name").autocomplete({
            source: function (request, callback) {
                var searchTerm = this.element.attr('data-search-term')
                var searchTermObject = {};
                searchTermObject[searchTerm] = request.term;
                $.getJSON(organisation_duplicate_search_url, searchTermObject, callback);
            },
            minLength: 3,
            select: function (event, ui) {
                var url = '/ops/organisation/' + ui.item.id + '/'
                window.open(url, '_blank ');
                event.preventDefault();
            },
            search: function (event, ui) {},
            response: function (event, ui) {
                window.len = ui.content.length;
                $('#ui-id-1.ui-autocomplete').next('.ui-helper-hidden-accessible').hide();
            },
            open: function (event, ui) {
                $('#ui-id-1.ui-autocomplete').prepend("<div class='bg-warning text-dark p-1' style='font-size: 14px;'>Are you trying to add any of these existing organisations?</div>");
                return false;
            },
            focus: function (event, ui) {},
            close: function (event, ui) {
                if (window.len > 0) {
                    $("ul.ui-autocomplete").hide();
                }
            }
        }).data("ui-autocomplete")._renderItem = function (ul, item) {

            if (item.details__trading_name !== null) {
                var trading_name = ' / ' + item.details__trading_name
            } else {
                var trading_name = ''
            }
            return $("<li></li>")
                .data("item.autocomplete", item)
                .append('<a>' + item.details__registered_name + trading_name + ' (' + item.details__type__name + ', ' + item.details__country__code + ')')
                .appendTo(ul);
        };
    };

    if ($('#id_organisation_details_form_pre-trading_name').length) {
        $("#id_organisation_details_form_pre-trading_name").autocomplete({
            source: function (request, callback) {
                var searchTerm = this.element.attr('data-search-term')
                var searchTermObject = {};
                searchTermObject[searchTerm] = request.term;
                $.getJSON(organisation_duplicate_search_url, searchTermObject, callback);
            },
            minLength: 3,
            select: function (event, ui) {
                var url = '/ops/organisation/' + ui.item.id + '/'
                window.open(url, '_blank ');
                event.preventDefault();
            },
            search: function (event, ui) {},
            response: function (event, ui) {
                window.len = ui.content.length;
                $('#ui-id-2.ui-autocomplete').next('.ui-helper-hidden-accessible').hide();
            },
            open: function (event, ui) {
                $('#ui-id-2.ui-autocomplete').prepend("<div class='bg-warning text-dark p-1' style='font-size: 14px;'>Are you trying to add any of these existing organisations?</div>");
                return false;
            },
            focus: function (event, ui) {},
            close: function (event, ui) {
                if (window.len > 0) {
                    $("ul.ui-autocomplete").hide();
                }
            }
        }).data("ui-autocomplete")._renderItem = function (ul, item) {

            if (item.details__trading_name !== null) {
                var trading_name = ' / ' + item.details__trading_name
            }
            else {
                var trading_name = ''
            }
            return $("<li></li>")
                .data("item.autocomplete", item)
                .append('<a>' + item.details__registered_name + trading_name + ' (' + item.details__type__name + ', ' + item.details__country__code + ')')
                .appendTo(ul);
        };
    };

});
