let primaryTypeField = document.querySelector('#id_organisation_details_form_pre-type');
let secondaryTypesField = document.querySelector('#id_organisation_details_form_pre-secondary_types');

$(document).ready(function () {
  $(primaryTypeField).on('change', updateSecondaryTypeList);
  $(secondaryTypesField).on('select2:open', updateSecondaryTypeList);
  $(primaryTypeField).trigger('change');
})


function updateSecondaryTypeList(){
  let primaryType = $(primaryTypeField).select2('data')[0]?.id;

  if (primaryType == 1002) {
    secondaryTypesField.disabled = true;
  } else {
    secondaryTypesField.disabled = false;
    secondaryTypesField.querySelectorAll('option').forEach((el) => {
      el.disabled = el.value === primaryType;
    });
  }
}
