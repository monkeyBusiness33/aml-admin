
const formWrapperEl = $('#mission_fueling_requirements')
const fuelRequiredCheck = $('.fuel_required')


function fuelRequiredClickProcessing(field) {

  let checkedState = field.checked
  if (checkedState) {
    let oppositeCheckbox = $(field).closest('td').find('.fuel_required').not(field);
    oppositeCheckbox.prop('checked', false)
  }
}

function updateFuelDetailsFieldsState() {
  $(".fuel_required_cell").each(function (i, cell) {
    let fuelRequired = false
    let fuelRequiredCheckboxes = $(cell).find('.fuel_required')

    // Disable everything in case if servicing is not requested for this turnaround
    let isServicingRequested = $(this).data('servicing_requested')
    if (isServicingRequested === 'no') {
      fuelRequiredCheckboxes.each(function (index, checkbox) {
        $(checkbox).prop('checked', false)
        $(checkbox).attr('disabled', true)
      })
    }

    // Check is there are at least one "Fuel Required?" value checked
    fuelRequiredCheckboxes.each(function (index, checkbox) {
      let checkedState = checkbox.checked
      if (checkedState) {
        fuelRequired = true
        return ''
      }
    });

    let formPrefix = $(cell).data('form-prefix');
    let qtyFieldId = '#id_' + formPrefix + '-fuel_quantity'
    let unitFieldId = '#id_' + formPrefix + '-fuel_unit'
    let pristRequiredFieldId = '#id_' + formPrefix + '-fuel_prist_required'

    if (fuelRequired) {
      $(qtyFieldId).attr('disabled', false)
      $(qtyFieldId).attr('required', true)

      $(unitFieldId).attr('disabled', false)
      $(unitFieldId).attr('required', true)

      $(pristRequiredFieldId).attr('disabled', false)
    } else {
      $(qtyFieldId).val(null)
      $(qtyFieldId).attr('disabled', true)

      $(unitFieldId).val(null)
      $(unitFieldId).attr('disabled', true)

      $(pristRequiredFieldId).attr('disabled', true)
      $(pristRequiredFieldId).prop('checked', false)
    }

  });
}


formWrapperEl.change(function () {
  updateFuelDetailsFieldsState()
});

formWrapperEl.ready(function () {
  updateFuelDetailsFieldsState()
});

fuelRequiredCheck.click(function (e) {
  fuelRequiredClickProcessing(e.target)
});
