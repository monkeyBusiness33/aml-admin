$('#fuel_pricing_market_pld_billable_organisations_list').ready(function () {
  if ($('#fuel_pricing_market_pld_billable_organisations_list').length) {
    // Table related actions
    $('#fuel_pricing_market_pld_billable_organisations_list_datatable').on('click', 'tbody tr td.url_source_col', function (event) {
      var cell = $(event.currentTarget);
      var cell_html = cell.html();
      var url = $($.parseHTML(cell_html)).data('url');
      window.open(url, '_self').focus();
    })
    $('#fuel_pricing_market_pld_billable_organisations_list_datatable').on('draw.dt', function (event) {
      $("#fuel_pricing_market_pld_billable_organisations_list .toolbar").remove();
      $("#fuel_pricing_market_pld_billable_organisations_list_datatable_filter").detach()
      load_modal_buttons()
      $(".popover").popover('hide');
      load_popovers()
      load_tooltips()
    });
  }
});
