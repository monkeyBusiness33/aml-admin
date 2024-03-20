form_instance = document.getElementById('fuel_pricing_form')

addAllEventListeners()

let accordion_arrows = document.querySelectorAll('.accordion-arrow')
accordion_arrows.forEach(arrow => {
  setAccordionArrow(arrow)

  let accordion_button = arrow.parentElement.parentElement
  accordion_button.addEventListener('click', function () {
    setAccordionArrow(arrow)
  })
})

let private_checkbox = document.querySelector('[name*="applies_to_private"]')
let commercial_checkbox = document.querySelector('[name*="applies_to_commercial"]')

private_checkbox.addEventListener('click', () => {
  if (!private_checkbox.checked && !commercial_checkbox.checked) {
    private_checkbox.checked = true
  }
})
commercial_checkbox.addEventListener('click', () => {
  if (!private_checkbox.checked && !commercial_checkbox.checked) {
    commercial_checkbox.checked = true
  }
})

$(document).ready(function () {
  let band_type_fields = $(`[name*="band_uom"]`)
  initializeBandPricing(band_type_fields)
})


function reInitializeSelect2() {
  $('.django-select2').each(function () {
    $(this).djangoSelect2("destroy")
    $(this).djangoSelect2({
      dropdownParent: $(this).parent(),
      width: '100%'
    });
  });
}


function addAllEventListeners() {

  let add_section_buttons = document.querySelectorAll('.add-form-section')
  let delete_section_buttons = document.querySelectorAll('.delete-form-section')
  let add_band_buttons = document.querySelectorAll('.new-band-button')
  let delete_band_buttons = document.querySelectorAll('.delete-row')
  let band_type_fields = $(`[name*="band_uom"]`)
  let revert_button = document.querySelector('.revert-button')

  add_section_buttons.forEach(button => {
    button.addEventListener('click', addFormSection)
  })

  delete_section_buttons.forEach(button => {
    button.addEventListener('click', deleteFormSection)
  })

  add_band_buttons.forEach(button => {
    button.addEventListener('click', alterBandInput)
  })

  revert_button.addEventListener('click', revertToDefault)

  if (delete_band_buttons != null) {
    delete_band_buttons.forEach(button => {
      button.addEventListener('click', function () {
        this.parentElement.parentElement.remove()
      })
    })
  }
  band_type_fields.each(function () {
    $(this).on('select2:select', function () {
      alterBandPricing($(this))
    })
    $(this).on('select2:clear', function () {
      alterBandPricing($(this))
    })
  })

  document.querySelectorAll('[id*="-inclusive_taxes"]').forEach((el) => {
    $(el).on('change', updateInclusiveTaxesElements);
    $(el).trigger('change');
  });
}

function revertToDefault() {
  let form_num = this.parentElement.id.match(/\d+/)[0]

  let band_rows = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row`)
  let band_pricing_field = document.querySelector(`#id_new-pricing-${form_num}-band_differential_value`)
  let form_pricing_field = document.querySelector(`#id_new-pricing-${form_num}-differential_value`)

  let i = 0
  band_rows.forEach(row => {
    if (i > 0) {
      row.remove()
    }
    i++
  })

  band_pricing_field.required = false
  band_pricing_field.parentElement.parentElement.classList.add('d-none')
  form_pricing_field.required = true
  form_pricing_field.parentElement.parentElement.classList.remove('d-none')

  let band_fields = document.querySelectorAll(`
        #collapseBandAccordion-${form_num} .band input
    `)

  let band_type_field = $(`#collapseBandAccordion-${form_num} [name*="band_uom"]`)

  band_type_field.val('').trigger('change')

  band_fields.forEach(field => {
    field.value = ""
  })

  alterRequiredAttribute(form_num, 'remove')

}

function alterRequiredAttribute(form_num, action) {

  let band_fields = document.querySelectorAll(
    `#collapseBandAccordion-${form_num} .band-row [name*="band_start"],
         #collapseBandAccordion-${form_num} .band-row [name*="band_end"]`)

  band_fields.forEach(field => {
    if (action == 'add') {
      field.required = true
      if (field.previousElementSibling) {
        field.previousElementSibling.classList.add('required')
      }
    } else {
      field.required = false
      if (field.previousElementSibling) {
        field.previousElementSibling.classList.remove('required')
      }
    }
  })

  let amount_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row [name*="differential_value"]`)

  amount_fields.forEach(field => {
    if (action == 'add') {
      field.required = true
      if (field.previousElementSibling) {
        field.previousElementSibling.classList.add('required')
      }
    } else {
      field.required = false
      if (field.previousElementSibling) {
        field.previousElementSibling.classList.remove('required')
      }
    }
  })
}


function initializeBandPricing(band_type_fields) {
  band_type_fields.each(function () {
    alterBandPricing($(this))
  })
}


function alterBandPricing(band_field) {

  selected_data = band_field.select2('data')[0].text
  let field = document.getElementById(band_field.attr('id'))
  let form_num = field.id.match(/\d+/)[0]
  let band_rows = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row`)

  if (selected_data != "" && selected_data != "---------" || band_rows.length > 1) {
    alterAmountField(form_num, 'add')
    alterRequiredAttribute(form_num, 'add')

  } else if (selected_data == "" && band_rows.length == 1) {

    alterRequiredAttribute(form_num, 'remove')
  }
}


function alterAmountField(form_num, action) {
  let band_pricing_field = document.querySelector(`#id_new-pricing-${form_num}-band_differential_value`)
  let form_pricing_field = document.querySelector(`#id_new-pricing-${form_num}-differential_value`)
  let band_pricing_label = document.querySelector(`#collapseBandAccordion-${form_num} .band-row [for*="differential_value"]`)

  if (action == 'add') {
    band_pricing_field.required = true
    band_pricing_field.parentElement.parentElement.classList.remove('d-none')
    if (band_pricing_field.value == '') {
      band_pricing_field.value = form_pricing_field.value
    }
    band_pricing_label.classList.add('required')
    form_pricing_field.value = ''
    form_pricing_field.required = false
    form_pricing_field.parentElement.parentElement.classList.add('d-none')
  } else {
    band_pricing_field.required = false
    band_pricing_field.parentElement.parentElement.classList.add('d-none')
    band_pricing_label.classList.remove('required')
    band_pricing_field.value = ''
    form_pricing_field.value = band_pricing_field.value
    form_pricing_field.required = true
    form_pricing_field.parentElement.parentElement.classList.remove('d-none')
  }
}


function alterBandInput() {
  let form_num = this.parentElement.id.match(/\d+/)[0]
  let band_row = document.querySelectorAll(`#bandAccordion-${form_num} .band-row`)
  let row_num = band_row.length
  let band_pricing_div = document.querySelector(`#collapseBandAccordion-${form_num} .band-differential-value`)

  if (band_pricing_div.classList.contains('d-none')) {
    alterAmountField(form_num, 'add')
  }

  let new_band_row = band_row[row_num - 1].cloneNode(true)

  let labels = new_band_row.querySelectorAll('label')
  labels.forEach(label => {
    label.remove()
  })
  let bands = new_band_row.querySelectorAll('input:not([name*="start"])')
  let start_band = new_band_row.querySelector('[name*="start"]')
  let end_band = new_band_row.querySelector('[name*="end"]')
  let pricing_amount = new_band_row.querySelector('[name*="band_pricing"]')
  start_band.value = parseInt(bands[0].value) + 1
  start_band.parentElement.parentElement.classList.remove('existing')
  bands.forEach(band => {
    band.value = ""
    band.parentElement.parentElement.classList.remove('existing')
  })

  if (band_row.length == 1) {
    let new_div = document.createElement('div')
    new_div.classList.add('col', 'md-4', 'mb-3', 'deletion-col')
    let delete_band_button = document.createElement('button')
    delete_band_button.classList.add('fas', 'fa-minus', 'text-danger', 'delete-row')
    delete_band_button.type = 'button'
    delete_band_button.addEventListener('click', function () {
      this.parentElement.parentElement.remove()
    })

    new_div.append(delete_band_button)
    new_band_row.append(new_div)
  } else {
    let delete_band_button = new_band_row.querySelector('.delete-row')
    delete_band_button.addEventListener('click', function () {
      this.parentElement.parentElement.remove()
    })
  }

  let insert_before = document.querySelector(`#bandAccordion-${form_num} .insert-before-band`)
  this.parentElement.insertBefore(new_band_row, insert_before)
  new_band_row.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));


  alterBandFieldNumbering(form_num)


}


function alterBandFieldNumbering(form_num) {
  let band_start_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-start:not(.existing) input`)
  let band_end_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-end:not(.existing) input`)
  let band_pricing_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-differential-value:not(.existing) input`)

  let i = 1
  band_start_fields.forEach(field => {
    field.id = `id_new-pricing-0-band_start-additional-0-${i}`
    field.name = `new-pricing-0-band_start-additional-0-${i}`
    i++
  })

  i = 1
  band_end_fields.forEach(field => {
    field.id = `id_new-pricing-0-band_end-additional-0-${i}`
    field.name = `new-pricing-0-band_end-additional-0-${i}`
    i++
  })

  i = 1
  band_pricing_fields.forEach(field => {
    field.id = `id_new-pricing-0-band_differential_value-additional-0-${i}`
    field.name = `new-pricing-0-band_differential_value-additional-0-${i}`
    i++
  })

}


function setAccordionArrow(button) {
  if (button.parentElement.parentElement.classList.contains('collapsed')) {
    button.classList.add('accordion-closed')
    button.classList.remove('accordion-open')
  } else {
    button.classList.add('accordion-open')
    button.classList.remove('accordion-closed')
  }
}


let volumeRatioLabels = $('label[for*="volume_conversion_ratio_override"]');
let fuelFields = $('[name$="-fuel"]');
let pricingUnitFields = $('[name*="differential_pricing_unit"]');
let pricingIndexFields = $('[name*="pricing_index"]');

// fuelFields.each(function (i, el) {
//   let form_number = el.id.match(/\d+/)[0]
//   $(el).on('change', () => showDefaultVolumeRatioUnitsAndRate(form_number))
// });
//
// pricingUnitFields.each(function (i, el) {
//   let form_number = el.id.match(/\d+/)[0]
//   $(el).on('change', () => showDefaultVolumeRatioUnitsAndRate(form_number))
// });
//
// pricingIndexFields.each(function (i, el) {
//   let form_number = el.id.match(/\d+/)[0]
//   $(el).on('change', () => showDefaultVolumeRatioUnitsAndRate(form_number))
// });
//
// function showDefaultVolumeRatioUnitsAndRate(form_num) {
//   let subLabel = $(volumeRatioLabels[form_num]).find('.volume-ratio-units-default');
//   let fuel = fuelFields[form_num];
//   let pricing_unit = pricingUnitFields[form_num];
//   let pricing_index = pricingIndexFields[form_num];
//   if ($(fuel).val() && $(pricing_unit).val() && $(pricing_index).val()) {
//     $.ajax({
//       type: 'POST',
//       url: default_volume_conversion_ratio_url,
//       headers: {
//         'X-CSRFToken': getCSRFToken(),
//         'sessionid': getCookie('sessionid')
//       },
//       data: {
//         'fuel_pk': $(fuel).val(),
//         'unit_pk': $(pricing_unit).val(),
//         'index_details_pk': $(pricing_index).val(),
//       },
//       success: function (resp) {
//         if (resp.success === 'true') {
//           subLabel.text(
//             `Default: ${resp.from} => ${resp.to}:
//             ${resp.rate} ( ${resp.fuel} )`);
//         } else {
//           console.log(resp);
//           subLabel.text('');
//         }
//       },
//       error: function (resp) {
//         subLabel.text('');
//       }
//     });
//     subLabel.text('');
//   } else {
//     subLabel.text('');
//   }
// }
//
// $('form').each(function (i, el) {
//   showDefaultVolumeRatioUnitsAndRate(i);
// });


function updateInclusiveTaxesElements() {
  let formNum = this.id.match(/\d+/)[0];
  let inclusiveTaxesField = document.querySelector(`#id_new-pricing-${formNum}-inclusive_taxes`)
  let cascade_to_fees_checkbox = document.querySelector(`#id_new-pricing-${formNum}-cascade_to_fees`)
  if ($(inclusiveTaxesField).val().includes('A')) {
    $(inclusiveTaxesField).val(['A']);
    $(inclusiveTaxesField).find('option[value!="A"]').prop('disabled', true);
  } else {
    $(inclusiveTaxesField).find('option').prop('disabled', false);
  }

  if (!$(inclusiveTaxesField).val().length) {
    $(cascade_to_fees_checkbox).prop('disabled', true);
  } else {
    $(cascade_to_fees_checkbox).prop('disabled', false);
  }
}
