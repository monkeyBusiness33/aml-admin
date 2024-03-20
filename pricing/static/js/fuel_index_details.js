// Make each row clickable and redirect to relevant supplier agreement
$('#index_pricing_associated_agreement_pricing_list').ready(function () {
  if ($('#index_pricing_associated_agreement_pricing_list').length) {
    // Table related actions
    $('#index_pricing_associated_agreement_pricing_list_datatable').on('click', 'tbody tr td:not(.dataTables_row-tools)', function (event) {
      var row = $(event.currentTarget).parent('tr');
      var cell = row.find('td.url_source_col')
      var cell_html = cell.html();
      var url = $($.parseHTML(cell_html)).data('url');
      window.open(url, '_self').focus();
    })
    $('#index_pricing_associated_agreement_pricing_list_datatable').on('draw.dt', function (event) {
      $("#index_pricing_associated_agreement_pricing_list .toolbar").remove();
      $("#index_pricing_associated_agreement_pricing_list_datatable_filter").detach()
      load_modal_buttons()
      $(".popover").popover('hide');
      load_popovers()
      load_tooltips()
    });
  }
});
