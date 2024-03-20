form_instance = document.getElementById('fuel_pricing_form')

reformatSections()
toggleDeleteButtonDisabledAttr()
addAllEventListeners()

let accordion_arrows = document.querySelectorAll('.accordion-arrow')
accordion_arrows.forEach(arrow => {
  setAccordionArrow(arrow)

  let accordion_button = arrow.parentElement.parentElement
  accordion_button.addEventListener('click', function () {
    setAccordionArrow(arrow)
  })
})

$(document).ready(function () {
  let band_type_fields = $(`[name*="band_uom"]`)
  initializeBandPricing(band_type_fields)
})


function addAllEventListeners() {

  let add_section_buttons = document.querySelectorAll('.add-form-section')
  let delete_section_buttons = document.querySelectorAll('.delete-form-section')
  let add_band_buttons = document.querySelectorAll('.new-band-button')
  let delete_band_buttons = document.querySelectorAll('.delete-row')
  let band_type_fields = $(`[name*="band_uom"]`)
  let revert_buttons = document.querySelectorAll('.revert-button')

  add_section_buttons.forEach(button => {
    button.addEventListener('click', addFormSection)
  })

  delete_section_buttons.forEach(button => {
    button.addEventListener('click', deleteFormSection)
  })

  add_band_buttons.forEach(button => {
    button.addEventListener('click', alterBandInput)
  })

  revert_buttons.forEach(button => {
    button.addEventListener('click', revertToDefault)
  })

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

  document.querySelectorAll('[id*="-inclusive_taxes"]').forEach((el) => {
    $(el).on('change', updateInclusiveTaxesElements);

    // Update fields for all already shown forms on load
    if (!el.closest('.form-section').classList.contains('d-none')) {
      $(el).trigger('change');
    }
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

  let band_start_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-start input`)
  let band_end_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-end input`)
  let band_type_field = $(`#collapseBandAccordion-${form_num} [name*="band_uom"]`)

  band_type_field.val('').trigger('change')

  band_start_fields.forEach(field => {
    field.value = ""
  })

  band_end_fields.forEach(field => {
    field.value = ""
  })

  alterRequiredAttribute(form_num, 'remove')
}


function initializeBandPricing(band_type_fields) {
  band_type_fields.each(function () {
    alterBandPricing($(this))
  })
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
  start_band.value = parseInt(bands[0].value) + 1
  bands.forEach(band => {
    band.value = ""
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
  let band_start_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-start input`)
  let band_end_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-end input`)
  let band_pricing_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-differential-value input`)

  if (band_start_fields.length > 1) {
    let i = 0
    band_start_fields.forEach(field => {
      if (i > 0) {
        field.id = `id_new-pricing-${form_num}-band_start-additional-${form_num}-${i}`
        field.name = `new-pricing-${form_num}-band_start-additional-${form_num}-${i}`
      }
      i++
    })

    i = 0
    band_end_fields.forEach(field => {
      if (i > 0) {
        field.id = `id_new-pricing-${form_num}-band_end-additional-${form_num}-${i}`
        field.name = `new-pricing-${form_num}-band_end-additional-${form_num}-${i}`
      }
      i++
    })

    i = 0
    band_pricing_fields.forEach(field => {
      if (i > 0) {
        field.id = `id_new-pricing-${form_num}-band_differential_value-additional-${form_num}-${i}`
        field.name = `new-pricing-${form_num}-band_differential_value-additional-${form_num}-${i}`
      }
      i++
    })
  }
}


function addFormSection() {

  let form_sections = document.querySelectorAll('.d-none.form-section')
  form_sections[0].classList.remove('d-none')
  alterFormSectionInput(form_sections[0])

  toggleDeleteButtonDisabledAttr()

}

function alterFormSectionInput(form_section, action) {
  let form_fields = form_section.querySelectorAll('input, select, textarea')
  let delete_field = form_section.querySelector('[name*=DELETE]')

  let revert_button = form_section.querySelector('.revert-button')
  revert_button.click()

  if (action == 'delete') {
    form_fields.forEach(field => {

      if (field.type !== 'checkbox' && field !== delete_field) {
        field.value = '';
        field.required = false;
      }

      field.required = false
      if (field.nodeName == 'SELECT') {
        select_field = $(field)
        select_field.val(null).trigger('change')
      }
    })
    delete_field.checked = true
  } else {
    delete_field.checked = false
  }
}

function toggleDeleteButtonDisabledAttr() {
  let form_sections = document.querySelectorAll('.form-section:not(.d-none)')
  let delete_section_buttons = document.querySelectorAll('.delete-form-section')

  if (form_sections.length == 1) {
    delete_section_buttons[0].disabled = true
  } else {
    delete_section_buttons.forEach(button => {
      button.disabled = false
    })
  }
}


function deleteFormSection() {

  let form_sections = document.querySelectorAll('.form-section:not(.d-none)')
  let delete_section_buttons = document.querySelectorAll('.delete-form-section')

  if (form_sections.length > 1) {
    this.parentElement.parentElement.parentElement.classList.add('d-none')
    alterFormSectionInput(this.parentElement.parentElement.parentElement, 'delete')
  }

  if (form_sections.length == 2) {
    delete_section_buttons[0].disabled = true
  } else {
    delete_section_buttons[0].disabled = false
  }

}


function reformatSections() {
  let header_titles = document.querySelectorAll('.form-section-title')
  let form_sections = document.querySelectorAll('.fuel-form-body')

  let i = 1
  header_titles.forEach(title => {
    title.innerHTML = `Pricing #${i}`
    i++
  })

  let n = 1
  form_sections.forEach(section => {
    n % 2 == 0 ? section.style.background = '#11182713' : section.style.background = "white"
    n++
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

let post_button = document.querySelector('.post-button')
let modal_cancel = document.querySelector('.add-new-row')

modal_cancel.addEventListener('click', () => {
  addMissingRows()
})

post_button.addEventListener('click', function (e) {

  // e.preventDefault()

  let visible_forms = document.querySelectorAll('.form-section:not(.d-none)')
  missing_main_form_numbers = []
  missing_main_form_data = []
  missing_sub_form_numbers = []
  missing_sub_form_data = []
  all_missing_forms = []
  form_valid_for_missing = []
  let missing_key_fields = false

  if (visible_forms.length == 1) {
    let destination_type = document.querySelector(`[name*="-0-destination_type"]`)
    let location = document.querySelector(`[name*="-0-location"]`)
    if (location.value == '' || destination_type.value == '') {
      missing_key_fields = true
    }
    if (destination_type.value != 'ALL') {
      all_missing_forms.push(0)
    }
  } else {
    let skip_these_forms = []

    // Preprocessing
    let private_forms = []
    let commercial_forms = []
    let both_forms = []

    for (let i = 0; i < visible_forms.length; i++) {
      let destination_type = document.querySelector(`[name*="-${i}-destination_type"]`)
      let is_private = document.querySelector(`[name*="-${i}-applies_to_private"]`)
      let is_commercial = document.querySelector(`[name*="-${i}-applies_to_commercial"]`)
      if (destination_type.value != 'ALL') {
        if (is_private.checked && is_commercial.checked) {
          both_forms.push(i)
        } else if (is_private.checked) {
          private_forms.push(i)
        } else if (is_commercial.checked) {
          commercial_forms.push(i)
        }
      }
    }

    let forms_to_process = both_forms.concat(commercial_forms, private_forms)

    for (let main_iterator = 0; main_iterator < forms_to_process.length; main_iterator++) {
      let index = forms_to_process[main_iterator]
      let matching_forms = []

      // Skip a form if it's already matched with another one...
      if (skip_these_forms.includes(index)) {
        continue
      }

      // Build form data (have to make sure that we are checking for identical forms)
      let location = document.querySelector(`[name*="-${index}-location"]`)
      let destination_type = document.querySelector(`[name*="-${index}-destination_type"]`)

      if (location.value == '' || destination_type.value == '') {
        missing_key_fields = true
        break
      }

      let private_checkbox = document.querySelector(`[name*="-${index}-applies_to_private"]`)
      let commercial_checkbox = document.querySelector(`[name*="-${index}-applies_to_commercial"]`)
      let fuel = document.querySelector(`[name*="-${index}-fuel"]`)
      let delivery_method = document.querySelector(`[name*="-${index}-delivery_method"]`)
      let flight_type = document.querySelector(`[name*="-${index}-flight_type"]`)

      let ipa = document.querySelector(`[name*="-${index}-ipa"]`)

      missing_main_form_data.push(`${location.value} - ${destination_type.value}`)
      missing_main_form_numbers.push(index)
      skip_these_forms.push(index)

      if (destination_type.value == 'DOM') {
        var possibly_missing_destination = 'INT'
      } else if (destination_type.value == 'INT') {
        var possibly_missing_destination = 'DOM'
      }

      if (private_checkbox.checked && commercial_checkbox.checked) {
        var valid_for = 'Private/Commercial'
        missing_main_form_data.push(`${location.value} - ${possibly_missing_destination}`)
        missing_main_form_numbers.push(index)
      } else if (private_checkbox.checked) {
        var valid_for = 'Private'
      } else if (commercial_checkbox.checked) {
        var valid_for = 'Commercial'
      }

      let data_list = [location.value, fuel.value, delivery_method.value, flight_type.value, ipa.value]

      for (let sub_iterator = 1; sub_iterator < forms_to_process.length; sub_iterator++) {
        let sub_index = forms_to_process[sub_iterator]
        let matching_form_found = true

        // ... and also don't check the form with itself
        if (index == sub_index) {
          continue
        }

        let sub_location = document.querySelector(`[name*="-${sub_index}-location"]`)
        let sub_fuel = document.querySelector(`[name*="-${sub_index}-fuel"]`)
        let sub_delivery_method = document.querySelector(`[name*="-${sub_index}-delivery_method"]`)
        let sub_flight_type = document.querySelector(`[name*="-${sub_index}-flight_type"]`)
        let sub_ipa = document.querySelector(`[name*="-${sub_index}-ipa"]`)

        let sub_data_list = [sub_location.value, sub_fuel.value, sub_delivery_method.value, sub_flight_type.value, sub_ipa.value]

        // If something is not identical, then we are not looking for that form
        for (let i = 0; i < data_list.length; i++) {
          if (data_list[i] !== sub_data_list[i]) {
            matching_form_found = false
            break;
          }
        }

        if (matching_form_found) {
          matching_forms.push(sub_index)
        }

        // When at the last iteration, check
        if (sub_iterator + 1 == forms_to_process.length) {
          let main_resolved = false

          if (valid_for == 'Private/Commercial') {
            form_valid_for_missing.push(`${index}-Commercial`)
            form_valid_for_missing.push(`${index}-Private`)
          }

          matching_forms.forEach(function (form_index, iterator) {
            let overlap_valid_for = false
            let sub_private_checkbox = document.querySelector(`[name*="-${form_index}-applies_to_private"]`)
            let sub_commercial_checkbox = document.querySelector(`[name*="-${form_index}-applies_to_commercial"]`)
            let sub_destination_type = document.querySelector(`[name*="-${form_index}-destination_type"]`)
            let sub_location = document.querySelector(`[name*="-${form_index}-location"]`)

            if (sub_private_checkbox.checked && sub_commercial_checkbox.checked) {
              var sub_valid_for = 'Private/Commercial'
            } else if (sub_private_checkbox.checked) {
              var sub_valid_for = 'Private'
            } else if (sub_commercial_checkbox.checked) {
              var sub_valid_for = 'Commercial'
            }

            if (valid_for == 'Private/Commercial' && (sub_valid_for == 'Private' || sub_valid_for == 'Commercial') ||
              sub_valid_for == 'Private/Commercial' && (valid_for == 'Private' || valid_for == 'Commercial')) {
              overlap_valid_for = true
            }

            skip_these_forms.push(form_index)

            if (overlap_valid_for && !main_resolved) {
              missing_sub_form_data.push(`${sub_location.value} - ${sub_destination_type.value}`)
              missing_sub_form_numbers.push(form_index)

              let missing_form_remains = true
              if (sub_valid_for == 'Private' && form_valid_for_missing.includes(`${index}-Private`)) {
                form_valid_for_missing.splice(form_valid_for_missing.indexOf(`${index}-Private`), 1)
                missing_sub_form_data.pop()
                missing_sub_form_numbers.pop()
                missing_main_form_data.pop()
                missing_main_form_numbers.pop()
                missing_form_remains = false
              }

              if (sub_valid_for == 'Commercial' && form_valid_for_missing.includes(`${index}-Commercial`)) {
                form_valid_for_missing.splice(form_valid_for_missing.indexOf(`${index}-Commercial`), 1)
                missing_sub_form_data.pop()
                missing_sub_form_numbers.pop()
                missing_main_form_data.pop()
                missing_main_form_numbers.pop()
                missing_form_remains = false
              }

              if (!missing_form_remains && iterator + 1 == matching_forms.length) {
                main_resolved = true

              }

            } else if (((destination_type.value == 'DOM' && sub_destination_type.value == 'INT') ||
              (destination_type.value == 'INT' && sub_destination_type.value == 'DOM')) && !main_resolved) {

              missing_sub_form_data.push(`${sub_location.value} - ${sub_destination_type.value}`)
              missing_sub_form_numbers.push(form_index)

              if (valid_for == sub_valid_for) {
                missing_sub_form_data.pop()
                missing_sub_form_numbers.pop()
                missing_main_form_data.pop()
                missing_main_form_numbers.pop()
                main_resolved = true

                // Delete the other challenge when they match
                if (valid_for == 'Private/Commercial' && sub_valid_for == 'Private/Commercial') {
                  missing_main_form_data.pop()
                  missing_main_form_numbers.pop()
                }
              }
            } else { // If no match, no overlap
              if (valid_for == 'Private/Commercial' && sub_valid_for == 'Private/Commercial') {
                // Remove one challenge from main, as to not display twice
                missing_main_form_data.pop()
                missing_main_form_numbers.pop()
              } else {
                missing_sub_form_data.push(`${sub_location.value} - ${sub_destination_type.value}`)
                missing_sub_form_numbers.push(form_index)
              }
            }
          })
        }
      }
    }
  }

  if (all_missing_forms.length == 0) {
    all_missing_forms = missing_main_form_numbers.concat(missing_sub_form_numbers)
  }

  if (all_missing_forms.length > 0 && !missing_key_fields) {
    e.preventDefault()

    let modal_label = document.querySelector('#notificationModalLabel')
    modal_label.innerHTML = `Missing Pricing Entries`

    let modal_text = document.querySelector('.modal-text')

    let missing_list_data = ''
    all_missing_forms.forEach(index => {
      let location = $(`[name*="-${index}-location"]`).select2('data')[0].text
      let destination = $(`[name*="-${index}-destination_type"]`).select2('data')[0].text
      let private_checkbox = document.querySelector(`[name*="-${index}-applies_to_private"]`)
      let commercial_checkbox = document.querySelector(`[name*="-${index}-applies_to_commercial"]`)

      if (destination == 'Domestic') {
        var missing = 'International'
      } else if (destination == 'International') {
        var missing = 'Domestic'
      }

      if (form_valid_for_missing.includes(`${index}-Private`) && form_valid_for_missing.includes(`${index}-Commercial`)) {
        var valid_for_missing = 'Private/Commercial'
      } else if (form_valid_for_missing.includes(`${index}-Private`)) {
        var valid_for_missing = 'Private'
      } else if (form_valid_for_missing.includes(`${index}-Commercial`)) {
        var valid_for_missing = 'Commercial'
      } else {
        if (private_checkbox.checked && commercial_checkbox.checked) {
          var valid_for_missing = 'Private/Commercial'
        } else if (commercial_checkbox.checked) {
          var valid_for_missing = 'Commercial'
        } else if (private_checkbox.checked) {
          var valid_for_missing = 'Private'
        }
      }

      missing_list_data = missing_list_data + `<li>${location} - ${valid_for_missing} - ${missing} entry</li>`

    })

    modal_text.innerHTML = `The pricing details entered appear to be incomplete, with the following entries missing:<br>
                                <ul>${missing_list_data}</ul>
                                Would you like to add the missing pricing?`

    let notification_modal = new bootstrap.Modal(document.getElementById('notificationModal'))
    notification_modal.show()
  }

})

function addMissingRows() {
  let form_sections = document.querySelectorAll('.d-none.form-section')
  let k = 0

  all_missing_forms.forEach(index => {
    form_sections[k].classList.remove('d-none')

    let private_checkbox = document.querySelector(`[name*="-${index}-applies_to_private"]`)
    let commercial_checkbox = document.querySelector(`[name*="-${index}-applies_to_commercial"]`)
    let location = document.querySelector(`[name*="-${index}-location"]`)
    let fuel = document.querySelector(`[name*="-${index}-fuel"]`)
    let delivery_method = document.querySelector(`[name*="-${index}-delivery_method"]`)
    let flight_type = document.querySelector(`[name*="-${index}-flight_type"]`)
    let destination_type = document.querySelector(`[name*="-${index}-destination_type"]`)
    let ipa = document.querySelector(`[name*="-${index}-ipa"]`)
    let pricing_unit = document.querySelector(`[name*="-${index}-differential_pricing_unit"]`)
    let client = document.querySelector(`[name*="-${index}-client"]`)
    let inclusive_taxes = document.querySelector(`[name*="-${index}-inclusive_taxes"]`)
    let cascade_to_fees = document.querySelector(`[name*="-${index}-cascade_to_fees"]`)
    let specific_handler = document.querySelector(`[name*="-${index}-specific_handler"]`)
    let specific_apron = document.querySelector(`[name*="-${index}-specific_apron"]`)
    let specific_hookup_method = document.querySelector(`[name*="-${index}-specific_hookup_method"]`)
    let fuel_index = document.querySelector(`[name*="-${index}-fuel_index"]`)
    let pricing_index = document.querySelector(`[name*="-${index}-pricing_index"]`)
    let index_period_is_lagged = document.querySelector(`[name*="-${index}-index_period_is_lagged"]`)
    let index_period_is_grace = document.querySelector(`[name*="-${index}-index_period_is_grace"]`)
    let band_uom = document.querySelector(`[name*="-${index}-band_uom"]`)
    let band_row = document.querySelectorAll(`.form-${index} .band-row `)
    let band_start = document.querySelectorAll(`[name*="-${index}-band_start"]`)
    let band_end = document.querySelectorAll(`[name*="-${index}-band_end"]`)

    let new_location = form_sections[k].querySelector('[name*="location"]')
    let new_private_checkbox = form_sections[k].querySelector(`[name*="applies_to_private"]`)
    let new_commercial_checkbox = form_sections[k].querySelector(`[name*="applies_to_commercial"]`)
    let new_fuel = form_sections[k].querySelector(`[name*="fuel"]`)
    let new_delivery_method = form_sections[k].querySelector(`[name*="delivery_method"]`)
    let new_flight_type = form_sections[k].querySelector(`[name*="flight_type"]`)
    let new_destination_type = form_sections[k].querySelector(`[name*="destination_type"]`)
    let new_ipa = form_sections[k].querySelector(`[name*="ipa"]`)
    let new_pricing_unit = form_sections[k].querySelector(`[name*="differential_pricing_unit"]`)
    let new_client = form_sections[k].querySelector(`[name*="client"]`)
    let new_inclusive_taxes = form_sections[k].querySelector(`[name*="inclusive_taxes"]`)
    let new_cascade_to_fees = form_sections[k].querySelector(`[name*="cascade_to_fees"]`)
    let new_specific_handler = form_sections[k].querySelector(`[name*="specific_handler"]`)
    let new_specific_apron = form_sections[k].querySelector(`[name*="specific_apron"]`)
    let new_specific_hookup_method = form_sections[k].querySelector(`[name*="specific_hookup_method"]`)
    let new_fuel_index = form_sections[k].querySelector(`[name*="fuel_index"]`)
    let new_pricing_index = form_sections[k].querySelector(`[name*="pricing_index"]`)
    let new_index_period_is_lagged = form_sections[k].querySelector(`[name*="index_period_is_lagged"]`)
    let new_index_period_is_grace = form_sections[k].querySelector(`[name*="index_period_is_grace"]`)
    let new_band_uom = form_sections[k].querySelector(`[name*="band_uom"]`)

    if (private_checkbox.checked && commercial_checkbox.checked) {
      new_private_checkbox.checked = true
      new_commercial_checkbox.checked = true
    } else if (private_checkbox.checked) {
      new_private_checkbox.checked = true
      new_commercial_checkbox.checked = false
    } else if (commercial_checkbox.checked) {
      new_commercial_checkbox.checked = true
      new_private_checkbox.checked = false
    }

    new_index_period_is_lagged.checked = index_period_is_lagged.checked;
    new_index_period_is_grace.checked = index_period_is_grace.checked;

    if (destination_type.value == 'DOM') {
      missing_destination = 'INT'
    } else {
      missing_destination = 'DOM'
    }

    let location_name = $(location).select2('data')[0].text
    let ipa_name = $(ipa).select2('data')[0]?.text
    let pricing_unit_name = $(pricing_unit).select2('data')['0'].text
    let fuel_index_label = $(fuel_index).select2('data')['0'].text
    let pricing_index_label = $(pricing_index).select2('data')['0'].text

    let location_id = $(location).select2('data')[0].id
    let ipa_id = $(ipa).select2('data')[0]?.id
    let pricing_unit_id = $(pricing_unit).select2('data')['0'].id
    let fuel_index_id = $(fuel_index).select2('data')['0'].id
    let pricing_index_id = $(pricing_index).select2('data')['0'].id

    var location_option = new Option(location_name, location_id, true, true);
    $(new_location).append(location_option).trigger('change');

    var ipa_option = new Option(ipa_name, ipa_id, true, true);
    $(new_ipa).append(ipa_option).trigger('change');

    if ($(client).select2('data').length) {
        let client_name = $(client).select2('data')[0].text
        let client_id = $(client).select2('data')[0].id
        var client_option = new Option(client_name, client_id, true, true);
        $(new_client).append(client_option).trigger('change');
    }

    if ($(specific_handler).select2('data').length) {
      let specific_handler_name = $(specific_handler).select2('data')['0'].text
      let specific_handler_id = $(specific_handler).select2('data')['0'].id
      var specific_handler_option = new Option(specific_handler_name, specific_handler_id, true, true);
      $(new_specific_handler).append(specific_handler_option).trigger('change');
    }

    if ($(specific_apron).select2('data').length) {
      let specific_apron_name = $(specific_apron).select2('data')['0'].text
      let specific_apron_id = $(specific_apron).select2('data')['0'].id
      var specific_apron_option = new Option(specific_apron_name, specific_apron_id, true, true);
      $(new_specific_apron).append(specific_apron_option).trigger('change');
    }

    if ($(specific_hookup_method).select2('data').length) {
      let specific_hookup_method_name = $(specific_hookup_method).select2('data')['0'].text
      let specific_hookup_method_id = $(specific_hookup_method).select2('data')['0'].id
      var specific_hookup_method_option = new Option(specific_hookup_method_name, specific_hookup_method_id, true, true);
      $(new_specific_hookup_method).append(specific_hookup_method_option).trigger('change');
    }

    var pricing_unit_option = new Option(pricing_unit_name, pricing_unit_id, true, true);
    $(new_pricing_unit).append(pricing_unit_option).trigger('change');

    var fuel_index_option = new Option(fuel_index_label, fuel_index_id, true, true);
    $(new_fuel_index).append(fuel_index_option).trigger('change');

    var pricing_index_option = new Option(pricing_index_label, pricing_index_id, true, true);
    $(new_pricing_index).append(pricing_index_option).trigger('change');

    $(new_fuel).val($(fuel).val()).trigger('change')
    $(new_delivery_method).val($(delivery_method).val()).trigger('change')
    $(new_flight_type).val($(flight_type).val()).trigger('change')
    $(new_destination_type).val(missing_destination).trigger('change')

    $(new_inclusive_taxes).val($(inclusive_taxes).val()).trigger('change')
    new_cascade_to_fees.checked = cascade_to_fees.checked;

    $(new_band_uom).val($(band_uom).val()).trigger('change')

    let new_add_band_button = form_sections[k].querySelector('.new-band-button')

    for (let index = 0; index < band_row.length - 1; index++) {
      new_add_band_button.click()
    }

    let new_band_start = form_sections[k].querySelectorAll(`[name*="band_start"]`)
    let new_band_end = form_sections[k].querySelectorAll(`[name*="band_end"]`)

    let i = 0
    new_band_start.forEach(band => {
      band.value = band_start[i].value
      i++
    })

    i = 0
    new_band_end.forEach(band => {
      band.value = band_end[i].value
      i++
    })

    // Make sure that 'deleted' gets removed from comment on any created form
    alterFormSectionInput(form_sections[k]);

    k++
  })
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
