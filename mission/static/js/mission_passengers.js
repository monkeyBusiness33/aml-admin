$('#passengers_payload_section .formset-row').slice(0, min_pax).each(function (i, obj) {
  let removeButton = $(obj).find('.formset_row_del_btn')
  $(removeButton).prop('disabled', true);
  $(removeButton).data('persistent', true);
});

passengers_payload_section = $("#passengers_payload_section")

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


function identifier_trigger(){
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

passengers_payload_section.change(function () {
  identifier_trigger()
});
