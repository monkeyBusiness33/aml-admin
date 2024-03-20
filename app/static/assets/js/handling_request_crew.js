function disablePrimaryContactRemoving() {
  $('.formset_row').each(function (i, obj) {

    let isPrimaryContactCheckbox = $(obj).find('.is_primary_contact')
    let isPrimaryContactChecked = $(isPrimaryContactCheckbox).prop('checked');
    if (isPrimaryContactChecked) {
      let removeButton = $(obj).find('.formset_row_del_btn')
      $(removeButton).prop('disabled', true);
      $(removeButton).data('persistent', true);
    }
  });
}

function canUpdateMissionForPrimaryContactSync() {
  $('.formset_row').each(function (i, obj) {

    let isPrimaryContactCheckbox = $(obj).find('.is_primary_contact')
    let isPrimaryContactChecked = $(isPrimaryContactCheckbox).prop('checked');
    if (isPrimaryContactChecked) {
      let row = isPrimaryContactCheckbox.closest('tr')
      let can_update_mission_field = $(row).find(".can_update_mission").first()

      can_update_mission_field.prop('checked', isPrimaryContactChecked)
    }
  });
}


function updateTravelDocumentStatus(field) {
  let personSelect2Field = $(field)
  if (typeof personSelect2Field.select2('data') !== "undefined" && typeof personSelect2Field.select2('data')[0] !== "undefined") {
    let person_id = personSelect2Field.select2('data')[0].id
    let requestUrl = person_travel_document_status_url.replace(new RegExp("[0-9]", "g"), person_id)
    $.ajax({
      type: 'GET',
      url: requestUrl,
      headers: {
        'X-CSRFToken': getCSRFToken(),
        'sessionid': getCookie('sessionid')
      },
      success: function (response) {
        let travel_document_status = response.status_light_html + ' ' + response.files_download_icons
        $(field).closest('tr').find('.status-light-cell').html(travel_document_status);
        load_tooltips()
      },
    });
  }
}

handling_request_crew_form = $('#handling_request_crew')

handling_request_crew_form.ready(function () {
  canUpdateMissionForPrimaryContactSync()
});

handling_request_crew_form.change(function () {
  canUpdateMissionForPrimaryContactSync()
});

$('.person-select').on('change', function (e) {
  let field = e.target
  $(field).closest('div').find('.invalid-feedback').remove();
  updateTravelDocumentStatus(field)
});

load_tooltips()

$('.exclusive').click(function () {
  let checkedState = $(this).attr('checked');
  $('.exclusive').not($(this)).prop('checked', false);
  $(this).attr('checked', checkedState);
});
