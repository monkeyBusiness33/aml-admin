let differential_fields = document.querySelectorAll('[name*="differential"]')
differential_fields.forEach(field => {
  field.classList.add('set-width')
});

let discount_fields = document.querySelectorAll('[name*="discount_"]')
discount_fields.forEach(field => {
  field.classList.add('set-width')
});

let band_type_fields = document.querySelectorAll(`[name*="band_uom"]`)
band_type_fields.forEach(field => {
  toggleBandPricing(field)
})

band_type_fields.forEach(field => {
  $(field).on('select2:select', function () {
    toggleBandPricing(field)
  })
  $(field).on('select2:clear', function () {
    toggleBandPricing(field)
  })
})

let sub_rows = document.querySelectorAll('.sub')
sub_rows.forEach(row => {
  if (row.childElementCount != 7) {
    let needed_tds = 7 - row.childElementCount
    for (let index = 0; index < needed_tds; index++) {
      row.appendChild(document.createElement('td'))
    }
  }
})


let private_checkboxes = document.querySelectorAll('[name*="applies_to_private"]')
let commercial_checkboxes = document.querySelectorAll('[name*="applies_to_commercial"]')

private_checkboxes.forEach(checkbox => {
  checkbox.addEventListener('click', () => {
    let form_number = checkbox.id.match(/\d+/)[0]
    let commercial_checkbox = document.querySelector(`[name*="${form_number}-applies_to_commercial"]`)

    if (!checkbox.checked && !commercial_checkbox.checked) {
      commercial_checkbox.checked = true
    }
  })
})

commercial_checkboxes.forEach(checkbox => {
  checkbox.addEventListener('click', () => {
    let form_number = checkbox.id.match(/\d+/)[0]
    let private_checkbox = document.querySelector(`[name*="${form_number}-applies_to_private"]`)

    if (!checkbox.checked && !private_checkbox.checked) {
      private_checkbox.checked = true
    }
  })
})

let sidebar = document.getElementById('sidebarMenu')
let sidebar_toggle = document.getElementById('sidebar-toggle')

$(document).ready(() => {
  sidebar_collapse()
  reInitializeHiddenRows()
  removeInvalidOnDisabled()

  // The destroy alone fixes the modal error on load
  setTimeout(() => {
    reInitializeSelect2()
  }, 500)
})


function reInitializeSelect2() {
  $('.django-select2').each(function () {
    $(this).djangoSelect2("destroy")
    $(this).djangoSelect2({
      dropdownParent: $(this).parent(),
      width: '100%',
    });
  });
}

function toggleBandPricing(field) {

  let form_num = field.name.match(/\d+/)[0]
  let band_fields = document.querySelectorAll(`[name*="-${form_num}-band_start"], [name*="-${form_num}-band_end"]`)
  if (field.value == '') {
    band_fields.forEach(field => {
      field.disabled = true
      field.classList.remove('is-invalid')
    })
  } else {
    band_fields.forEach(field => {
      field.disabled = false
    })
  }

}


let form_fields = document.querySelectorAll('.form-row input, .form-row select, .form-modal input, .form-modal select, .form-modal textarea')

let form_row = document.querySelectorAll('.form-row.main')
let form_modal = document.querySelectorAll('.form-modal')

let button_pressed_input = document.querySelector('.button-pressed-input')
let footer_buttons = document.querySelectorAll('.button-row button')

footer_buttons.forEach(button => {
  button.addEventListener('click', function () {
    button_pressed_input.value = this.value
    form_fields.forEach(field => {
      if (field.disabled) {
        field.disabled = false
      }
      if (button_pressed_input.value != 'Supersede') {
        if (field.required) {
          field.required = false
        }
      } else {
        sidebar_collapse()
      }

    })
  })
})


function removeInvalidOnDisabled() {
  form_fields.forEach(field => {
    if (field.disabled) {
      field.classList.remove('is-invalid')
    }
  })
}


function reInitializeHiddenRows() {
  form_row.forEach(row => {
    let delete_checkbox = row.querySelector('[id*="DELETE"]')
    let hide_row_icon = row.querySelector('.hide-row')
    let child_rows = row.parentElement.querySelectorAll(`.form-${hide_row_icon.value - 1}.sub`)
    let child_fields = row.parentElement.querySelectorAll(`.form-${hide_row_icon.value - 1}.sub input, .form-${hide_row_icon.value - 1}.sub select`)

    if (delete_checkbox.checked) {
      row.classList.add('row-disabled')
      hide_row_icon.classList.remove('fa-trash', 'text-danger')
      hide_row_icon.classList.add('fa-recycle', 'text-success')

      let row_fields = row.querySelectorAll('input, select')
      row_fields.forEach(field => {
        field.disabled = true
        field.classList.remove('is-invalid')
      })
      child_rows.forEach(row => {
        row.classList.add('row-disabled')
      })
      child_fields.forEach(field => {
        field.disabled = true
        field.classList.remove('is-invalid')
      })
    }
  })
}

let hide_row_buttons = document.querySelectorAll('.hide-row')

hide_row_buttons.forEach(button => {
  button.addEventListener('click', hideFormRow)
})

function hideFormRow(e) {

  if (e.target.classList.contains('hide-row')) {

    let form_fields = form_row[this.value - 1].querySelectorAll('input:not(.table-date-input), select')
    let modal_fields = form_modal[this.value - 1].querySelectorAll('input, select, textarea')
    let delete_checkbox = form_row[this.value - 1].querySelector('[id*="DELETE"]')
    let header_date_checkbox = document.querySelector('.header-date-open')

    if (delete_checkbox.checked) {
      delete_checkbox.checked = false
    } else {
      delete_checkbox.checked = true
    }

    // Note: readOnly is not working for <select>
    form_fields.forEach(field => {
      if (field.disabled && !field.name.includes('-location')) {
        field.disabled = false
      } else {
        field.disabled = true
        field.classList.remove('is-invalid')
      }
    })

    modal_fields.forEach(field => {
      if (field.disabled) {
        field.disabled = false
      } else {
        field.disabled = true
        field.classList.remove('is-invalid')
      }
    })

    let child_rows = document.querySelectorAll(`.form-${this.value - 1}.sub`)
    let child_fields = document.querySelectorAll(`.form-${this.value - 1}.sub input, .form-${this.value - 1}.sub select`)

    if (form_row[this.value - 1].classList.contains('row-disabled')) {
      form_row[this.value - 1].classList.remove('row-disabled')
      this.classList.remove('fa-recycle', 'text-success')
      this.classList.add('fa-trash', 'text-danger')
      child_rows.forEach(row => {
        row.classList.remove('row-disabled')
      })
      child_fields.forEach(field => {
        if (!field.name.includes('amount_old')) {
          field.disabled = false
        }
      })
      let band_type_field = form_row[this.value - 1].querySelector(`[name*="band_uom"]`)
      toggleBandPricing(band_type_field)
    } else {
      form_row[this.value - 1].classList.add('row-disabled')
      this.classList.remove('fa-trash', 'text-danger')
      this.classList.add('fa-recycle', 'text-success')
      child_rows.forEach(row => {
        row.classList.add('row-disabled')
      })
      child_fields.forEach(field => {
        field.disabled = true
        field.classList.remove('is-invalid')
      })
    }

  }
}

let add_band_buttons = document.querySelectorAll('.add-row')
let delete_band_buttons = document.querySelectorAll('.delete-row')

add_band_buttons.forEach(button => {
  button.addEventListener('click', alterBandInput)
})

delete_band_buttons.forEach(button => {
  button.addEventListener('click', function () {
    this.parentElement.parentElement.parentElement.remove()
  })
})


function alterBandInput(e) {
  let form_num = this.id.match(/\d+/)[0];
  let pricingType = this.closest('table').id.includes('formula') ? 'formula' : 'discount';
  let pricingFieldName = pricingType === 'formula'
    ? 'differential_value'
    : this.closest('table').querySelector(`.form-row.form-${form_num}.main [name*='is_percentage']`).checked ? 'discount_percentage' : 'discount_amount';
  let band_row = e.target.closest('table').querySelectorAll(`.form-row.form-${form_num}`)
  let row_num = band_row.length

  let new_band_row = band_row[row_num - 1].cloneNode(true)
  let current_pricing = new_band_row.querySelectorAll(`[name*="differential_value_old"], [name*="amount_old"], [name*="percentage_old"]`)

  current_pricing.forEach(function (field) {
    if (field != null) {
      if (band_row.length == 2) {
        field.parentElement.remove()
      } else {
        field.remove()
      }
    }
  });

  let tax_info = new_band_row.querySelector('.tax-info')
  if (tax_info != null) {
    tax_info.remove()
  }

  let id_field = new_band_row.querySelector('[name*="id-additional"]')
  if (id_field != null) {
    id_field.parentElement.remove()
  }


  let labels = new_band_row.querySelectorAll('label')
  labels.forEach(label => {
    label.remove()
  })

  let end_band = new_band_row.querySelector('input:not([name*="start"])')
  let start_band = new_band_row.querySelector('[name*="start"]')
  let pricing_field = new_band_row.querySelector(`[name*="${pricingFieldName}"]`)

  if (end_band.value != '') {
    start_band.value = parseInt(end_band.value) + 1
    end_band.value = ''
  } else {
    start_band.value = ''
  }

  pricing_field.value = ''

  start_band.classList.remove('is-invalid')
  end_band.classList.remove('is-invalid')
  pricing_field.classList.remove('is-invalid')

  if (band_row.length == 2) {
    let new_div = document.createElement('div')
    new_div.classList.add('col', 'md-4', 'mb-3', 'deletion-col')
    let delete_band_button = document.createElement('button')
    delete_band_button.classList.add('fas', 'fa-minus', 'text-danger', 'delete-row')
    delete_band_button.type = 'button'
    delete_band_button.addEventListener('click', function () {
      this.parentElement.parentElement.parentElement.remove()
    })

    let add_button_div = new_band_row.querySelector('.add-col')

    new_div.append(delete_band_button)
    add_button_div.replaceWith(new_div)

  } else {
    let delete_band_button = new_band_row.querySelector('.delete-row')
    delete_band_button.addEventListener('click', function () {
      this.parentElement.parentElement.parentElement.remove()
    })
  }

  let insert_before = e.target.closest('table').querySelector(`.form-${form_num}.insert-before-band`)
  this.parentElement.parentElement.parentElement.parentElement.insertBefore(new_band_row, insert_before)
  new_band_row.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));


  alterBandFieldNumbering(form_num, pricingType)
}


function alterBandFieldNumbering(form_num, pricingType) {
  let tableIdSelector = pricingType === 'formula'
    ? '#formula_pricing_table'
    : '#discount_pricing_table';
  let pricingTable = document.querySelector(tableIdSelector)

  let band_start_fields = pricingTable.querySelectorAll(`.form-row.form-${form_num}.sub [name*="band_start"]`)
  let band_end_fields = pricingTable.querySelectorAll(`.form-row.form-${form_num}.sub [name*="band_end"]`)
  let band_pricing_fields = pricingTable.querySelectorAll(`.form-row.form-${form_num}.sub [name$="pricing_native_amount"], .form-row.form-${form_num}.sub [name*="pricing_native_amount-additional"]`)
  let band_discount_amount_fields = pricingTable.querySelectorAll(`.form-row.form-${form_num}.sub [name$="discount_amount"], .form-row.form-${form_num}.sub [name*="discount_amount-additional"]`)
  let band_discount_percentage_fields = pricingTable.querySelectorAll(`.form-row.form-${form_num}.sub [name$="discount_percentage"], .form-row.form-${form_num}.sub [name*="discount_percentage-additional"]`)
  let band_differential_fields = pricingTable.querySelectorAll(`.form-row.form-${form_num}.sub [name$="differential_value"], .form-row.form-${form_num}.sub [name*="discount_percentage-additional"]`)

  if (band_start_fields.length > 1) {
    let i = 0
    band_start_fields.forEach(field => {
      if (i > 0) {
        field.id = `id_existing-${pricingType}-pricing-${form_num}-band_start-additional-${form_num}-${i}`
        field.name = `existing-${pricingType}-pricing-${form_num}-band_start-additional-${form_num}-${i}`
      }

      i++
    })

    i = 0
    band_end_fields.forEach(field => {
      if (i > 0) {
        field.id = `id_existing-${pricingType}-pricing-${form_num}-band_end-additional-${form_num}-${i}`
        field.name = `existing-${pricingType}-pricing-${form_num}-band_end-additional-${form_num}-${i}`
      }
      i++
    })

    i = 0
    band_pricing_fields.forEach(field => {
      if (i > 0) {
        field.id = `id_existing-${pricingType}-pricing-${form_num}-band_pricing_amount-additional-${form_num}-${i}`
        field.name = `existing-${pricingType}-pricing-${form_num}-band_pricing_amount-additional-${form_num}-${i}`
      }
      i++
    })

    band_discount_amount_fields.forEach((field, i) => {
      if (i > 0) {
        field.id = `id_existing-${pricingType}-pricing-${form_num}-band_discount_amount-additional-${form_num}-${i}`
        field.name = `existing-${pricingType}-pricing-${form_num}-band_discount_amount-additional-${form_num}-${i}`
      }
    });

    band_discount_percentage_fields.forEach((field, i) => {
      if (i > 0) {
        field.id = `id_existing-${pricingType}-pricing-${form_num}-band_discount_percentage-additional-${form_num}-${i}`
        field.name = `existing-${pricingType}-pricing-${form_num}-band_discount_percentage-additional-${form_num}-${i}`
      }
    });

    band_differential_fields.forEach((field, i) => {
      if (i > 0) {
        field.id = `id_existing-${pricingType}-pricing-${form_num}-band_differential_value-additional-${form_num}-${i}`
        field.name = `existing-${pricingType}-pricing-${form_num}-band_differential_value-additional-${form_num}-${i}`
      }
    });
  }
}


document.querySelectorAll('[id*="-inclusive_taxes"]').forEach((el) => {
  $(el).on('change', updateInclusiveTaxesElements);
  $(el).trigger('change');
});


function updateInclusiveTaxesElements() {
  let inclusiveTaxesField = this.closest('.modal-body').querySelector('[id*="-inclusive_taxes"]')
  let cascade_to_fees_checkbox = this.closest('.modal-body').querySelector('[id*="-cascade_to_fees"]')
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


// Display default Volume Conversion Ratio value in Optional Details modal

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
//
// function showDefaultVolumeRatioUnitsAndRate(form_num) {
//   let subLabel = $(volumeRatioLabels[form_num]).find('.volume-ratio-units-default');
//   let fuel = fuelFields[form_num];
//   let pricing_unit = pricingUnitFields[form_num];
//   let pricing_index = pricingIndexFields[form_num];
//
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
// $('.form-modal>[id*="modal-optional"][id*="-formula"]').each(function (i, el) {
//   showDefaultVolumeRatioUnitsAndRate(i);
// });


document.querySelectorAll('[id*="-is_percentage"]').forEach((isPercentageInput) => {
  waitForElement(`.toggle-group [for*="${isPercentageInput.id}"]`).then((el) => {
    el.parentElement.parentElement.addEventListener('click', switchDiscountType);

    // Update fields for all already shown forms on load
    if (!el.closest('.form-row').classList.contains('d-none')) {
      el.parentElement.parentElement.firstChild.click();
    }
  });
});


function switchDiscountType() {
  let pricingTable = document.querySelector('#discount_pricing_table')
  let form_num = this.firstChild.id.match(/\d+/)[0];
  let band_pricing_fields = pricingTable.querySelectorAll(`[id*="id_existing-discount-pricing-${form_num}-band_discount_amount"]`)
  let band_percentage_fields = pricingTable.querySelectorAll(`[id*="id_existing-discount-pricing-${form_num}-band_discount_percentage"]`)
  let form_discount_unit_field = pricingTable.querySelector(`#id_existing-discount-pricing-${form_num}-pricing_discount_unit`)
  let form_pricing_field = pricingTable.querySelector(`#id_existing-discount-pricing-${form_num}-pricing_discount_amount`)
  let form_percentage_field = pricingTable.querySelector(`#id_existing-discount-pricing-${form_num}-pricing_discount_percentage`)
  let form_old_pricing_fields = pricingTable.querySelectorAll(`[id*="id_existing-discount-pricing-${form_num}-discount_amount_old"]`)
  let form_old_percentage_fields = pricingTable.querySelectorAll(`[id*="id_existing-discount-pricing-${form_num}-discount_percentage_old"]`)
  let isPercentage = this.firstChild.checked;

  if (isPercentage) {
    $(form_discount_unit_field).val(null).trigger('change')
    form_discount_unit_field.disabled = true
    form_percentage_field.classList.remove('d-none')
    form_pricing_field.classList.add('d-none')
    form_old_pricing_fields.forEach(function (field) {
      field.classList.add('d-none')
    });
    form_old_percentage_fields.forEach(function (field) {
      field.classList.remove('d-none')
    });
    band_pricing_fields.forEach(function (field) {
      field.classList.add('d-none')
    });
    band_percentage_fields.forEach(function (field) {
      field.classList.remove('d-none')
    });
  } else {
    form_discount_unit_field.disabled = false
    form_percentage_field.classList.add('d-none')
    form_pricing_field.classList.remove('d-none')
    form_old_pricing_fields.forEach(function (field) {
      field.classList.remove('d-none')
    });
    form_old_percentage_fields.forEach(function (field) {
      field.classList.add('d-none')
    });
    band_pricing_fields.forEach(function (field) {
      field.classList.remove('d-none')
    });
    band_percentage_fields.forEach(function (field) {
      field.classList.add('d-none')
    });
  }
}


function waitForElement(selector) {
  return new Promise(resolve => {
    if (document.querySelector(selector)) {
      return resolve(document.querySelector(selector));
    }

    const observer = new MutationObserver(mutations => {
      if (document.querySelector(selector)) {
        resolve(document.querySelector(selector));
        observer.disconnect();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
