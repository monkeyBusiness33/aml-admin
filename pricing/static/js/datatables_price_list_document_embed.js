$('.datatable_auto_compact_div').ready(function () {
    if ($('.datatable_auto_compact_div').length) {
        $('.datatable_auto_compact').each(function (index) {
            var datatable_id = $(this).attr('id')
            var datatable_url = $(this).attr('data-datatable-url')

            AjaxDatatableViewUtils.initialize_table(
                $(this),
                datatable_url, {
                    dom: 't',
                    "language": {
                        "lengthMenu": "_MENU_ entries per page",
                        "search": '',
                        "searchPlaceholder": "Search...",
                    },
                    autoWidth: false,
                    full_row_select: false,
                    scrollX: false,
                    iDisplayLength: 100,
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
            $(this).on('click', 'tbody tr', function (event) {
                var tr = event.currentTarget

                // Datatable Plus/Minus change helper start
                var has_next = $(tr).next('tr.details')
                if (has_next.length == 1){
                    var row_tools = $(tr).children('.dataTables_row-tools')
                    var plus = row_tools.find('.plus')
                    var minus = row_tools.find('.minus')
                    $(minus).removeClass('d-none').addClass('d-inline')
                    $(plus).removeClass('d-inline').addClass('d-none')
                }
                else {
                    var row_tools = $(tr).children('.dataTables_row-tools')
                    var plus = row_tools.find('.plus')
                    var minus = row_tools.find('.minus')
                    $(plus).removeClass('d-none').addClass('d-inline')
                    $(minus).removeClass('d-inline').addClass('d-none')
                }
                // Datatable Plus/Minus change helper end

            })

            $(this).on('draw.dt', function (event) {
                $("#" + datatable_id + "_filter").detach()
                load_modal_buttons()
                $(".popover").popover('hide');
                load_popovers()
                load_tooltips()
            });

            $(this).on('init.dt', function () {
                $(this).removeClass('datatable_auto_compact')
                table = $('.details')
                table.show()
            })

        });
    }
});

