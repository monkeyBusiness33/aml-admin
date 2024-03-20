$('#agreement_formula_pricing_list').ready(function () {
  if ($('#agreement_formula_pricing_list').length) {
    // Table related actions
    $('#agreement_formula_pricing_list_datatable').on('click', 'tbody tr td.url_source_col', function (event) {
      var cell = $(event.currentTarget);
      var cell_html = cell.html();
      var url = $($.parseHTML(cell_html)).data('url');
      window.open(url, '_self').focus();
    })
    $('#agreement_formula_pricing_list_datatable').on('draw.dt', function (event) {
      $("#agreement_formula_pricing_list .toolbar").remove();
      $("#agreement_formula_pricing_list_datatable_filter").detach()
      load_modal_buttons()
      $(".popover").popover('hide');
      load_popovers()
      load_tooltips()
    });
  }
});


$('#agreement_discount_pricing_list').ready(function () {
  if ($('#agreement_discount_pricing_list').length) {
    // Table related actions
    $('#agreement_discount_pricing_list_datatable').on('click', 'tbody tr td.url_source_col', function (event) {
      var cell = $(event.currentTarget);
      var cell_html = cell.html();
      var url = $($.parseHTML(cell_html)).data('url');
      window.open(url, '_self').focus();
    })
    $('#agreement_discount_pricing_list_datatable').on('draw.dt', function (event) {
      $("#agreement_discount_pricing_list .toolbar").remove();
      $("#agreement_discount_pricing_list_datatable_filter").detach()
      load_modal_buttons();
      $(".popover").popover('hide');
      load_popovers();
      load_tooltips();
    });
  }
});


$('#agreement_associated_fees_list').ready(function () {
  if ($('#agreement_associated_fees_list').length) {
    // Table related actions
    $('#agreement_associated_fees_list_datatable').on('click', 'tbody tr td.url_source_col', function (event) {
      var cell = $(event.currentTarget);
      var cell_html = cell.html();
      var url = $($.parseHTML(cell_html)).data('url');
      window.open(url, '_self').focus();
    })
    $('#agreement_associated_fees_list_datatable').on('draw.dt', function (event) {
      $("#agreement_associated_fees_list .toolbar").remove();
      $("#agreement_associated_fees_list_datatable_filter").detach()
      load_modal_buttons();
      $(".popover").popover('hide');
      load_popovers();
      load_tooltips();
      // resize_subtable_cols();
    });

    // resizeObserver.observe($('#agreement_associated_fees_list_datatable')[0]);
  }
});

$('#agreement_associated_taxes_list').ready(function () {
  if ($('#agreement_associated_taxes_list').length) {
    // Table related actions
    $('#agreement_associated_taxes_list_datatable').on('click', 'tbody tr td.url_source_col', function (event) {
      var cell = $(event.currentTarget);
      var cell_html = cell.html();
      var url = $($.parseHTML(cell_html)).data('url');
      window.open(url, '_self').focus();
    })
    $('#agreement_associated_taxes_list_datatable').on('draw.dt', function (event) {
      $("#agreement_associated_taxes_list .toolbar").remove();
      $("#agreement_associated_taxes_list_datatable_filter").detach()
      load_modal_buttons();
      $(".popover").popover('hide');
      load_popovers();
      load_tooltips();
      // resize_subtable_cols();
    });

    // resizeObserver.observe($('#agreement_associated_taxes_list_datatable')[0]);
  }
});

// When redirected from agreement creation, show modal to trigger pricing creation
let params = new URLSearchParams(window.location.search)
let pricing_type_select_modal_node = document.getElementById(pricing_type_select_modal_id);

if (params.get('from_creation') === `1`) {
  let pricing_type_select_modal = new bootstrap.Modal(pricing_type_select_modal_node);
  $('#modal_cancel_btn_id, .btn-close').on('click',  function (event) {
    window.history.replaceState({}, '', location.pathname);
    pricing_type_select_modal_node.remove();
    location.reload();
  });

  pricing_type_select_modal.show();
} else {
  pricing_type_select_modal_node.remove();
}
