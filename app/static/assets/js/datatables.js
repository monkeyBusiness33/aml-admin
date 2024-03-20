///////////////////////////////////////////////////////////////////////
// Shared functions for datatables rendering start
///////////////////////////////////////////////////////////////////////

var organisationOperationalStatusBackground = function (event) {
    var html_table = $(event.target);
    html_table.find('tr').each(function (index, item) {

        try {
            var row = $(item);
            text = row.children('td.organisation_status').first().html();
            var text = $($.parseHTML(text)).data('search')

            if (text == "ceased_trading") {
                row.addClass('datatable-organisation-ceased-trading');
            }
            else if (text == "sanctioned") {
                row.addClass('datatable-organisation-sanctioned');
            }
        } catch (err) {}

    });
}

var removeRowTools = function (event) {
    var html_table = $(event.target);
    html_table.find('tr').each(function (index, item) {

        try {
            var row = $(item);
            text = row.children(':not(td.dataTables_row-tools)').first().html();
            var text = $($.parseHTML(text))
            has_children = text.hasClass('has_children')

            var row_tools = row.children('td.dataTables_row-tools').first();
            if (!has_children) {
                row_tools.html('')
            }

        } catch (err) {}

    });
}


var handlingRequestDocumentsSignedStatus = function (event) {
  var html_table = $(event.target);
  html_table.find('tr').each(function (index, item) {

    try {
      let row = $(item);
      let text = row.children('td.sfr_documents_is_signed').first().html();
      text = $($.parseHTML(text)).data('hidden-value')

      if (text === "signed") {
        row.addClass('light-green-bg');
      } else if (text === "not_signed") {
        row.addClass('light-red-bg');
      }

    } catch (err) {
    }

  });
}

function load_role_permissions_grant_buttons(e) {
    $(".grant_perms_button").each(function () {
        $(this).click(function (e) {
          e.preventDefault()
            $.post($(this).attr('href'), {
                csrfmiddlewaretoken: getCSRFToken(),
                success: function (response) {
                    setTimeout(() => {
                        var table = $('#role_permissions_list_datatable').dataTable().api();
                        table.draw();
                    }, 150);
                },
            });
        });
    });
}

function handling_request_spf_v2_services(e) {

  // Move "SPF Reconciled" button to the pagination line
  let spfReconcileBtnClone = $("#spf_reconciled_btn").clone()
  spfReconcileBtnClone.prependTo('#sfr_spf_v2_services_list_datatable_paginate');
  spfReconcileBtnClone.removeClass('d-none')
  let paginationWrapper = $('#sfr_spf_v2_services_list_datatable_paginate')
  paginationWrapper.children('ul').addClass("d-inline-flex");

  $(".update-value").each(function () {
    $(this).change(function (e) {

      // Get target URL
      var url = $(this).data('href')

      // Get key and value from changed field
      var dataKey = $(this).data('value-key')
      if ($(this).is(':checkbox')) {
        var dataVal = $(this).is(":checked")
      } else {
        var dataVal = $(this).val()
      }

      // Submit data
      $.ajax({
        type: 'POST',
        url: url,
        data: {"csrfmiddlewaretoken": getCSRFToken(), "dataKey": dataKey, "dataVal": dataVal},
        success: function (response) {
          notyf.open({type: 'success', message: "Value updated"})
        },
        error: function (response) {
          notyf.open({type: 'error', message: "Update failed"})
        },
      })
    });
  });
}


function create_button(header_button_url, header_button_modal, header_button_text, header_button_icon, button_modal_size, button_perm) {
    if (header_button_url == '' | button_perm == false) {
        return false
    } else {
        var button_icon_html = ''
        if (typeof header_button_icon !== "undefined" && header_button_icon != '') {
            var button_icon_html = '<i class="fas ' + header_button_icon + '"></i> '
        }
        if (header_button_modal == 'True' | header_button_modal == true) {
            if (button_modal_size === undefined) {
                var button_modal_size = "#modal"
            }
            button_html = '<button class="modal_button_validation bs-modal btn btn-outline-primary ms-1" data-modal="' + button_modal_size  + '" \
            data-bs-toggle="tooltip" data-bs-placement="top" title="' + header_button_text + '" \
            data-form-url="' + header_button_url + '">' + button_icon_html + header_button_text + '</button>'
            return button_html
        }
        if (header_button_modal == 'False' | header_button_modal == false) {
            button_html = '<a class="btn btn-outline-primary ms-1" href="' + header_button_url + '">' + button_icon_html + header_button_text + '</button>'
            return button_html
        }
    }
}

function create_checkbox(checkbox_text, checkbox_name, checkbox_value, checkbox_perm) {
    if (checkbox_text == '' | checkbox_name == '' | checkbox_perm == false) {
        return false
    } else {
        checkbox_html = '<div class="datatable-checkbox-wrapper">' +
                        `<label for="id_${checkbox_name}" class="datatable-filter-checkbox-label">` + checkbox_text + '</label>' +
                        '<input type="checkbox" class="datatable-filter-checkbox" name="' + checkbox_name +
                        `" id="id_${checkbox_name}" value="' + checkbox_value + '">` +
                        '</div>'
        return checkbox_html
    }
}

function open_url(cell_clicked, url_cell_class, open_target = '_self') {
    // Function to open URL from the database row meta
    let row = cell_clicked.closest('tr')
    let cell_data = $(row).find(url_cell_class).first()
    let cell_html = cell_data.html()
    let url = $($.parseHTML(cell_html)).data('url')
    if (url !== 'None') {
        window.open(url, open_target).focus();
    }
}


// New function to open URL from the database row meta
function open_cell_url(cell_clicked, forced_target = '') {
  // Ignore row-tools and actions cells
  if ($(cell_clicked).hasClass('dataTables_row-tools') || $(cell_clicked).hasClass('actions')) {
    return;
  }

  // Define variables
  let target_url
  let target_window = ''

  // Try to find URL in currently clicked cell
  target_url = $($.parseHTML($(cell_clicked).html())).data('url')
  target_window = forced_target || $($.parseHTML($(cell_clicked).html())).data('target') || '_self'
  if (target_url && target_url !== 'None') {
    window.open(target_url, target_window).focus();
    return;
  }

  // Otherwise try to find URL in first cell of the row
  let row = cell_clicked.closest('tr')
  let cell_data = $(row).find(".url_source_col").not(".single_cell_link").first()

  // Try legacy class as fallback
  if (!cell_data.length) {
    cell_data = $(row).find(".organisation_reg_name").first()
  }

  target_url = $($.parseHTML(cell_data.html())).data('url')
  target_window = forced_target || $($.parseHTML(cell_data.html())).data('target') || '_self'

  if (target_url && target_url !== 'None') {
    window.open(target_url, target_window).focus();
  }

}



///////////////////////////////////////////////////////////////////////
// Shared functions for datatables rendering end
///////////////////////////////////////////////////////////////////////


///////////////////////////////////////////////////////////////////////
// Global shared datatables initialization block start
///////////////////////////////////////////////////////////////////////

$('.datatable_auto_compact_div').ready(function () {
    if ($('.datatable_auto_compact_div').length) {

        $('.datatable_auto_compact').each(function (index) {
            var datatable_id = $(this).attr('id')
            var datatable_url = $(this).attr('data-datatable-url')

            // Prevent repeated initialization
            if ( $.fn.DataTable.isDataTable('#' + datatable_id)) {
              return;
            }

            AjaxDatatableViewUtils.initialize_table(
                $(this),
                datatable_url, {
                    dom: 'fr<"datatable-buttons d-inline-block float-end me-2">tp',
                    "language": {
                        "lengthMenu": "_MENU_ entries per page",
                        "search": '',
                        "searchPlaceholder": "Search..."
                    },
                    processing: false,
                    autoWidth: false,
                    full_row_select: false,
                    scrollX: false
                }, {
                    // extra_data
                },
            );
            // Table related actions
            $(this).on('click', 'tbody td', function (event) {
                var td = event.currentTarget

                if (datatable_id == 'ipa_list_datatable') {
                    var row = td.closest('tr')
                    if (!$(td).hasClass('ipa_airport_link')) {
                        var cell_data = $(row).find(".ipa_link").first()
                    } else {
                        var cell_data = $(row).find(".ipa_airport_link").first()
                    }
                    var cell_html = cell_data.html()
                    var url = $($.parseHTML(cell_html)).data('url')
                    window.open(url, '_self').focus();
                } else if (datatable_id == 'ground_handlers_list_datatable') {
                    var row = td.closest('tr')
                    if (!$(td).hasClass('airport_link')) {
                        var cell_data = $(row).find(".organisation_link").first()
                    } else {
                        var cell_data = $(row).find(".airport_link").first()
                    }
                    var cell_html = cell_data.html()
                    var url = $($.parseHTML(cell_html)).data('url')
                    window.open(url, '_self').focus();
                } else if (datatable_id == 'person_current_positions_list_datatable' || datatable_id == 'person_previous_positions_list_datatable') {
                    if ($(td).hasClass('organisation_reg_name')) {
                        var row = td.closest('tr')
                        var cell_data = $(row).find(".organisation_reg_name").first()
                        var cell_html = cell_data.html()
                        var url = $($.parseHTML(cell_html)).data('url')
                        window.open(url, '_self').focus();
                    }
                } else {
                  open_cell_url(event.currentTarget)
                }

            })

            $(this).on('mouseup', 'tbody td', function (event) {
                // An alternative version of the above, to open urls in a new tab on middle mouse btn click

                // Middle mouse btn only
                if (event.which !== 2) {
                  return;
                }
                open_cell_url(event.currentTarget, '_blank')
            })

            $(this).on('draw.dt', function (event) {
                $("#" + datatable_id + "_filter").detach()
                removeRowTools(event)
                let primary_vat_rows = document.querySelectorAll('.main-vat')
                primary_vat_rows.forEach(row => {
                    row.parentElement.parentElement.style.backgroundColor = "#8692be"
                    row.parentElement.parentElement.style.color = "white"
                })
                handlingRequestDocumentsSignedStatus(event)

                if (datatable_id === 'sfr_spf_v2_services_list_datatable') {
                  handling_request_spf_v2_services()
                }

                load_modal_buttons()
                $(".popover").popover('hide');
                load_popovers()
                load_tooltips()
            });

        });
    }
});

$('.datatable_auto_div').ready(function () {
    if ($('.datatable_auto_div').length) {

        $('.datatable_auto').each(function (index) {
            var datatable_id = $(this).attr('id')
            var datatable_url = $(this).attr('data-datatable-uri')

            // Prevent repeated initialization
            if ( $.fn.DataTable.isDataTable('#' + datatable_id)) {
              return;
            }

            AjaxDatatableViewUtils.initialize_table(
                $('#' + datatable_id),
                datatable_url, {
                    dom: '<"toolbar d-inline-block ms-4 mt-1 align-middle">fr<"datatable-buttons d-inline-block float-end me-2">tlip',
                    "language": {
                        "lengthMenu": "_MENU_ entries from",
                        "info": "_TOTAL_ total.",
                        "search": '',
                        "searchPlaceholder": "Search..."
                    },
                    processing: false,
                    autoWidth: false,
                    full_row_select: false,
                    scrollX: false
                }, {
                    // extra_data
                    checkbox_filter_data: () => {
                        data = {};

                        $(".datatable-checkboxes input").each(function() {
                            data[$(this).attr('name')] = $(this).is(":checked");
                        });

                        return JSON.stringify(data);
                    }
                },
            );
            // Table related actions
            $(this).on('click', 'tbody td', function (event) {
                var td = event.currentTarget

                if (datatable_id == 'ipa_list_datatable') {
                    var row = td.closest('tr')
                    if (!$(td).hasClass('ipa_airport_link')) {
                        var cell_data = $(row).find(".ipa_link").first()
                    }
                    else {
                        var cell_data = $(row).find(".ipa_airport_link").first()
                    }
                    var cell_html = cell_data.html()
                    var url = $($.parseHTML(cell_html)).data('url')
                    window.open(url, '_self').focus();
                }
                else if (datatable_id == 'ground_handlers_list_datatable') {
                    var row = td.closest('tr')
                    if (!$(td).hasClass('airport_link')) {
                        var cell_data = $(row).find(".organisation_link").first()
                    } else {
                        var cell_data = $(row).find(".airport_link").first()
                    }
                    var cell_html = cell_data.html()
                    var url = $($.parseHTML(cell_html)).data('url')
                    window.open(url, '_self').focus();
                } else if (datatable_id === 'dod_requests_list_datatable') {
                    open_url(td, '.sfr_url', '_blank')
                }
                else {
                  open_cell_url(event.currentTarget)
                }
            })

            $(this).on('mouseup', 'tbody td', function (event) {
                // An alternative version of the above, to open urls in a new tab on middle mouse btn click

                // Middle mouse btn only
                if (event.which !== 2) {
                  return;
                }

                open_cell_url(event.currentTarget, '_blank');
            })

            $('#' + datatable_id).on('draw.dt', function (event) {
              // Process status selection field
              let status_field = $(".mission-status").children('select').first()
                status_field.on('change', function () {
                    // If "ALL" option selected - remove other options from selection
                    if (typeof status_field.select2('data')[0] !== "undefined") {
                        let values = status_field.select2('data')
                        let option_all = values.find(x => x.id==='0' && x.selected);
                        if (option_all) {
                            status_field.val(0)
                        }
                    }
                });
                organisationOperationalStatusBackground(event)
                if(event.target.id == 'official_taxes_list_datatable'){
                    officialTaxesStatusBackground(event)
                }
                removeRowTools(event)
                $('#' + datatable_id + '_wrapper' + ' div.toolbar').html('<h5 class="mb-0">' + page_title + '</h5>');
                $('#' + datatable_id + '_wrapper' + ' div.datatable-buttons').html(null);
                if (header_buttons_list !== '') {
                    var buttons_list = JSON.parse(header_buttons_list);
                    var buttons_html = $('#' + datatable_id + '_wrapper' + ' div.datatable-buttons');
                    buttons_list.forEach(function (arrayItem) {
                        var button = create_button(
                            arrayItem.button_url,
                            arrayItem.button_modal,
                            arrayItem.button_text,
                            arrayItem.button_icon,
                            arrayItem.button_modal_size,
                            arrayItem.button_perm
                        )
                        if (button !== false) {
                            buttons_html.append(button)
                        }
                    });
                }
                if (header_checkbox_list !== '') {
                    $('#' + datatable_id + '_filter').addClass('d-flex flex-column');

                    if (!$('.datatable-checkboxes').length) {
                        $('#' + datatable_id + '_filter').append('<div class="datatable-checkboxes d-flex float-end"></div>');
                        $('#' + datatable_id + '_wrapper' + ' div.datatable-checkboxes').html(null);
                        var checkbox_list = JSON.parse(header_checkbox_list);
                        var checkboxes_html = $('#' + datatable_id + '_wrapper' + ' div.datatable-checkboxes');
                        checkbox_list.forEach(function (arrayItem) {
                            var checkbox = create_checkbox(
                                arrayItem.checkbox_text,
                                arrayItem.checkbox_name,
                                arrayItem.checkbox_perm,
                            )
                            if (checkbox !== false) {
                                checkboxes_html.append(checkbox)
                            }
                        });
                    }

                    $('.datatable-checkboxes input').on('change', function(e) {
                        $('table.dataTable').DataTable().ajax.reload(null, false);
                    });
                }
                load_modal_buttons()
                $(".popover").popover('hide');
                load_popovers()
                load_tooltips()
              if (datatable_id === 'role_permissions_list_datatable') {
                load_role_permissions_grant_buttons()
              }
            });

        });
    }
});

$('.ajax-datatable').ready(function () {
    $(this).on('draw.dt', function(event) {
        // Clear popups on each table redraw (as sometimes they would get permanently stuck on screen)
        $('.tooltip').hide();

        // Additional actions for multiple-choice filters

        // Convert select filters to multiple select2 based on column class
        let multiple_select_filter_cols = $('.multiple-select-filter-col select')

        if (multiple_select_filter_cols.length) {
            multiple_select_filter_cols.prop('multiple', 'multiple');
            multiple_select_filter_cols.select2();

            // Remove default blank option
            $('.multiple-select-filter-col option').filter(function(){
                return ($(this).val().trim()=="" && $(this).text().trim()=="");
            }).remove();
        }

    });

})

///////////////////////////////////////////////////////////////////////
// Global shared datatables initialization block end
///////////////////////////////////////////////////////////////////////

///////////////////////////////////////////////////////////////////////
// Organisations pages datatables initialization block start
///////////////////////////////////////////////////////////////////////

$('#aircraft_operator_fleet_list').ready(function () {
    if ($('#aircraft_operator_fleet_list').length) {
        AjaxDatatableViewUtils.initialize_table(
            $('#aircraft_operator_fleet_list_datatable'),
            aircraft_operator_fleet_datatable_uri, {
                dom: 'fr<"datatable-buttons d-inline-block float-end me-2">tp',
                "language": {
                    "lengthMenu": "_MENU_ entries per page",
                    "search": '',
                    "searchPlaceholder": "Search..."
                },
                processing: false,
                autoWidth: false,
                full_row_select: false,
                scrollX: false
            }, {
                // extra_data
            },
        );
        // Table related actions
        $('#aircraft_operator_fleet_list_datatable').on('draw.dt', function (event) {
            $("#aircraft_operator_fleet_list_datatable_filter").detach()
            load_modal_buttons()
            $(".popover").popover('hide');
            load_popovers()
            load_tooltips()
        });
    }
});

$('#airport_ground_handlers_list').ready(function () {
    if ($('#airport_ground_handlers_list').length) {
        AjaxDatatableViewUtils.initialize_table(
            $('#airport_ground_handlers_list_datatable'),
            airport_ground_handlers_datatable_uri, {
                dom: 'fr<"datatable-buttons d-inline-block float-end me-2">tp',
                "language": {
                    "lengthMenu": "_MENU_ entries per page",
                    "search": '',
                    "searchPlaceholder": "Search..."
                },
                processing: false,
                autoWidth: false,
                full_row_select: false,
                scrollX: false
            }, {
                // extra_data
            },
        );
        // Table related actions
        $('#airport_ground_handlers_list_datatable').on('click', 'tbody tr', function (event) {
            var row = event.currentTarget
            var cell_data = $(row).find(".organisation_reg_name").first()
            var cell_html = cell_data.html()
            // var cell = row.cells[1]
            // var cell_data = cell.innerHTML
            var url = $($.parseHTML(cell_html)).data('url')
            window.open(url, '_self').focus();
        })
        $('#airport_ground_handlers_list_datatable').on('draw.dt', function (event) {
            $("#airport_ground_handlers_list_datatable_filter").detach()
            load_modal_buttons()
            $(".popover").popover('hide');
            load_popovers()
            load_tooltips()
        });
    }
});

$('#airport_ipa_list').ready(function () {
    if ($('#airport_ipa_list').length) {
        AjaxDatatableViewUtils.initialize_table(
            $('#airport_ipa_list_datatable'),
            airport_ipa_list_datatable_uri, {
                dom: 'fr<"datatable-buttons d-inline-block float-end me-2">tp',
                "language": {
                    "lengthMenu": "_MENU_ entries per page",
                    "search": '',
                    "searchPlaceholder": "Search..."
                },
                processing: false,
                autoWidth: false,
                full_row_select: false,
                scrollX: false
            }, {
                // extra_data
            },
        );
        // Table related actions
        $('#airport_ipa_list_datatable').on('click', 'tbody tr', function (event) {
            var row = event.currentTarget
            var cell_data = $(row).find(".organisation_reg_name").first()
            var cell_html = cell_data.html()
            // var cell = row.cells[1]
            // var cell_data = cell.innerHTML
            var url = $($.parseHTML(cell_html)).data('url')
            window.open(url, '_self').focus();
        })
        $('#airport_ipa_list_datatable').on('draw.dt', function (event) {
            $("#airport_ipa_list_datatable_filter").detach()
            load_modal_buttons()
            $(".popover").popover('hide');
            load_popovers()
            load_tooltips()
        });
    }
});

$('#airport_based_organisations_list').ready(function () {
    if ($('#airport_based_organisations_list').length) {
        AjaxDatatableViewUtils.initialize_table(
            $('#airport_based_organisations_list_datatable'),
            airport_based_organisations_list_datatable_uri, {
                dom: 'fr<"datatable-buttons d-inline-block float-end me-2">tp',
                "language": {
                    "lengthMenu": "_MENU_ entries per page",
                    "search": '',
                    "searchPlaceholder": "Search..."
                },
                processing: false,
                autoWidth: false,
                full_row_select: false,
                scrollX: false
            }, {
                // extra_data
            },
        );
        // Table related actions
        $('#airport_based_organisations_list_datatable').on('click', 'tbody tr', function (event) {
            var row = event.currentTarget
            var cell_data = $(row).find(".organisation_reg_name").first()
            var cell_html = cell_data.html()
            // var cell = row.cells[1]
            // var cell_data = cell.innerHTML
            var url = $($.parseHTML(cell_html)).data('url')
            window.open(url, '_self').focus();
        })
        $('#airport_based_organisations_list_datatable').on('draw.dt', function (event) {
            $("#airport_based_organisations_list_datatable_filter").detach()
            load_modal_buttons()
            $(".popover").popover('hide');
            load_popovers()
            load_tooltips()
        });
    }
});

$('#organisation_documents_list').ready(function () {
    if ($('#organisation_documents_list').length) {
        AjaxDatatableViewUtils.initialize_table(
            $('#organisation_documents_list_datatable'),
            organisation_documents_datatable_uri, {
                dom: 'fr<"datatable-buttons d-inline-block float-end me-2">tp',
                "language": {
                    "lengthMenu": "_MENU_ entries per page",
                    "search": '',
                    "searchPlaceholder": "Search..."
                },
                processing: false,
                autoWidth: false,
                full_row_select: false,
                scrollX: false
            }, {
                // extra_data
            },
        );
        // Table related actions
        // $('#organisation_documents_list_datatable').on('click', 'tbody tr', function (event) {
        //     var row = event.currentTarget
        //     var cell_data = $(row).find(".organisation_reg_name").first()
        //     var cell_html = cell_data.html()
        //     // var cell = row.cells[1]
        //     // var cell_data = cell.innerHTML
        //     var url = $($.parseHTML(cell_html)).data('url')
        //     window.open(url, '_self').focus();
        // })
        $('#organisation_documents_list_datatable').on('draw.dt', function (event) {
            $("#organisation_documents_list_datatable_filter").detach()
            load_modal_buttons()
            $(".popover").popover('hide');
            load_popovers()
            load_tooltips()
        });
    }
});

/////////////////////////////////////
// Official Taxes datatable functions
/////////////////////////////////////

var officialTaxesStatusBackground = function (event) {
    var html_table = $(event.target);
    html_table.find('tr').each(function (index, item) {

        try {
            var row = $(item);
            text_service = row.children('td.service').first().html();
            text_fuel = row.children('td.fuel').first().html();
            var text = $($.parseHTML(text)).data('search')

            if (text_service == "✕" && text_fuel == '✕') {
                row.addClass('tax-status-missing');
            }
            else if (text_service == "✓" && text_fuel == '✓') {
                row.addClass('tax-status-ok');
            } else if (text_service == '✕' || text_fuel == '✕') {
                row.addClass('tax-status-partial')
            }
        } catch (err) {}

    });
}
