let fuel_fee_forms = document.querySelector('#id_new-fuel-fee-TOTAL_FORMS')
let fuel_fee_rate_forms = document.querySelector('#id_fuel-fee-rate-TOTAL_FORMS')
let categoryField = document.querySelector('[id$="-fuel_fee_category"]')
let form_instance = document.getElementById('fuel_fee_form')

addAllEventListeners()

$(document).ready(function(){
    let band_type_fields = $(`[name*="band_uom"]`)
    let weight_band_type_fields = $(`[name$="weight_band"]`)

    initializeBandPricing(weight_band_type_fields)
    initializeBandPricing(band_type_fields)

    $(categoryField).trigger('change');
})


let accordion_arrows = document.querySelectorAll('.accordion-arrow')
accordion_arrows.forEach(arrow => {
    setAccordionArrow(arrow)

    let accordion_button = arrow.parentElement.parentElement
    accordion_button.addEventListener('click', function(){
        setAccordionArrow(arrow)
    })
})


function addAllEventListeners(){
    let add_band_buttons = document.querySelectorAll('.new-band-button')
    let delete_band_buttons = document.querySelectorAll('.delete-row')
    let band_type_fields = $(`[name*="band_uom"]`)
    let weight_band_type_fields = $(`[name$="weight_band"]`)
    let revert_button = document.querySelector('.revert-button')

    add_band_buttons.forEach(button => {
        button.addEventListener('click', alterBandInput)
    })

    revert_button.addEventListener('click', revertToDefault)

    if(delete_band_buttons != null){
        delete_band_buttons.forEach(button => {
            button.addEventListener('click', function() {
                this.parentElement.parentElement.remove()
            })
        })
    }
    band_type_fields.each(function() {
        $(this).on('select2:select', function() {
            alterBandPricing($(this))
        })
        $(this).on('select2:clear', function(){
            alterBandPricing($(this))
        })
    })

    weight_band_type_fields.each(function() {
        $(this).on('select2:select', function() {
            alterBandPricing($(this))
        })
        $(this).on('select2:clear', function(){
            alterBandPricing($(this))
        })
    })

    document.querySelectorAll('select[id*="-specific_handler"]').forEach((handlerField) => {
      waitForElement(`.toggle-group [for*="${handlerField.id}"]`).then((el) => {
        $(handlerField).on('change', updateSpecificHandlerCheckbox);
        // Update fields for all already shown forms on load
        $(handlerField).trigger('change');
      });
    });

    $(categoryField).on('change', categoryUpdate);
}


function revertToDefault(){
    let form_num = this.parentElement.id.match(/\d+/)[0]

    let band_rows = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row`)
    let band_pricing_field = document.querySelector(`#id_fuel-fee-rate-${form_num}-band_pricing_native_amount`)
    let form_pricing_field = document.querySelector(`#id_fuel-fee-rate-${form_num}-pricing_native_amount`)

    let i = 0
    band_rows.forEach(row => {
        if(i > 0){
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

    let band_type_field = $(`#collapseBandAccordion-${form_num} [name*="quantity_band_uom"]`)
    let weight_band_type_field = $(`#collapseBandAccordion-${form_num} [name$="weight_band"]`)

    band_type_field.val('').trigger('change')
    weight_band_type_field.val('').trigger('change')

    band_fields.forEach(field => {
        field.value = ""
    })

    alterRequiredAttribute(band_type_field, form_num, 'remove')
    alterRequiredAttribute(weight_band_type_field, form_num, 'remove')
}


function initializeBandPricing(band_type_fields){
    band_type_fields.each(function() {
        alterBandPricing($(this))
    })
}


function alterRequiredAttribute(band_field, form_num, action){

    if(band_field[0].name.includes('quantity_band_uom')){
        let band_fields = document.querySelectorAll(
        `#collapseBandAccordion-${form_num} .band-row [name*="quantity_band_start"],
         #collapseBandAccordion-${form_num} .band-row [name*="quantity_band_end"]` )

        band_fields.forEach(field => {
            if(action == 'add'){
                field.required = true
                if(field.previousElementSibling){
                    field.previousElementSibling.classList.add('required')
                }
            } else {
                field.required = false
                if(field.previousElementSibling){
                    field.previousElementSibling.classList.remove('required')
                }
            }
        })

    } else if (band_field[0].name.includes('weight_band')) {
        let band_fields = document.querySelectorAll(
            `#collapseBandAccordion-${form_num} .band-row [name*="weight_band_start"],
             #collapseBandAccordion-${form_num} .band-row [name*="weight_band_end"]` )

        band_fields.forEach(field => {
            if(action == 'add'){
                field.required = true
                if(field.previousElementSibling){
                    field.previousElementSibling.classList.add('required')
                }
            } else {
                field.required = false
                if(field.previousElementSibling){
                    field.previousElementSibling.classList.remove('required')
                }
            }
        })
    }

    let amount_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row [name*="band_pricing_native"]`)

    if(amount_fields.length == 1){
        amount_fields.forEach(field => {
            if(action == 'add'){
                field.required = true
                if(field.previousElementSibling){
                    field.previousElementSibling.classList.add('required')
                }
            } else {
                field.required = false
                if(field.previousElementSibling){
                    field.previousElementSibling.classList.remove('required')
                }
            }
        })
    }
}


function alterBandPricing(band_field){

    let selected_data = band_field.select2('data')[0].text
    let field = document.getElementById(band_field.attr('id'))
    let form_num = field.id.match(/\d+/)[0]
    let band_rows = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row`)

    if(selected_data != "" && selected_data != "---------" || band_rows.length > 1 && selected_data != "" && selected_data != "---------"){
        alterAmountField(form_num, 'add')
        alterRequiredAttribute(band_field, form_num, 'add')

    } else if (selected_data == "" || band_rows.length == 1) {
        alterRequiredAttribute(band_field, form_num, 'remove')
    }
}


function alterAmountField(form_num, action){
    let band_pricing_field = document.querySelector(`#id_fuel-fee-rate-${form_num}-band_pricing_native_amount`)
    let form_pricing_field = document.querySelector(`#id_fuel-fee-rate-${form_num}-pricing_native_amount`)
    let band_pricing_label = document.querySelector(`#collapseBandAccordion-${form_num} .band-row [for*="band_pricing_native"]`)

    if(action == 'add'){
        band_pricing_field.required = true
        band_pricing_field.parentElement.parentElement.classList.remove('d-none')
        if(band_pricing_field.value == ''){
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


function alterBandInput(){
    let form_num = this.parentElement.id.match(/\d+/)[0]
    let band_row = document.querySelectorAll(`#bandAccordion-${form_num} .band-row`)
    let band_pricing_div = document.querySelector(`#collapseBandAccordion-${form_num} .band-pricing-native`)
    let row_num = band_row.length

    if(band_pricing_div.classList.contains('d-none')){
        alterAmountField(form_num, 'add')
    }

    let new_band_row = band_row[row_num-1].cloneNode(true)

    let labels = new_band_row.querySelectorAll('label')
    labels.forEach(label => {
        label.remove()
    })
    let bands = new_band_row.querySelectorAll('input:not([name*="start"])')
    let start_bands = new_band_row.querySelectorAll('[name*="start"]')
    let pricing_field = new_band_row.querySelector('[name*="pricing_native_amount"]')
    pricing_field.required = true
    start_bands[0].value = parseInt(bands[0].value) + 1
    start_bands[1].value = parseInt(bands[1].value) + 1
    bands.forEach(band => {
        band.value = ""
    })

    if(band_row.length == 1){
        let new_div = document.createElement('div')
        new_div.classList.add('col', 'md-4', 'mb-3', 'deletion-col')
        let delete_band_button = document.createElement('button')
        delete_band_button.classList.add('fas', 'fa-minus', 'text-danger', 'delete-row')
        delete_band_button.type = 'button'
        delete_band_button.addEventListener('click', function() {
            this.parentElement.parentElement.remove()
        })

        new_div.append(delete_band_button)
        new_band_row.append(new_div)
    } else {
        let delete_band_button = new_band_row.querySelector('.delete-row')
        delete_band_button.addEventListener('click', function() {
            this.parentElement.parentElement.remove()
        })
    }

    let insert_before = document.querySelector(`#bandAccordion-${form_num} .insert-before-band`)
    this.parentElement.insertBefore(new_band_row, insert_before)
    new_band_row.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));

    alterBandFieldNumbering(form_num)
}


function alterBandFieldNumbering(form_num){
    let band_start_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-start input`)
    let band_end_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-end input`)

    let weight_band_start_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .weight-band-start input`)
    let weight_band_end_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .weight-band-end input`)

    let band_pricing_fields = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-pricing-native input`)

    if(band_start_fields.length > 1){
        let i = 0
        band_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_fuel-fee-rate-${form_num}-quantity_band_start-additional-${form_num}-${i}`
                field.name = `fuel-fee-rate-${form_num}-quantity_band_start-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        band_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_fuel-fee-rate-${form_num}-quantity_band_end-additional-${form_num}-${i}`
                field.name = `fuel-fee-rate-${form_num}-quantity_band_end-additional-${form_num}-${i}`
            }
            i++
        })
        i = 0
        weight_band_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_fuel-fee-rate-${form_num}-weight_band_start-additional-${form_num}-${i}`
                field.name = `fuel-fee-rate-${form_num}-weight_band_start-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        weight_band_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_fuel-fee-rate-${form_num}-weight_band_end-additional-${form_num}-${i}`
                field.name = `fuel-fee-rate-${form_num}-weight_band_end-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        band_pricing_fields.forEach(field => {
            if(i > 0){
                field.id = `id_fuel-fee-rate-${form_num}-band_pricing_native_amount-additional-${form_num}-${i}`
                field.name = `fuel-fee-rate-${form_num}-band_pricing_native_amount-additional-${form_num}-${i}`
            }
            i++
        })
    }
}


function setAccordionArrow(button){
    if(button.parentElement.parentElement.classList.contains('collapsed')){
        button.classList.add('accordion-closed')
        button.classList.remove('accordion-open')
    } else {
        button.classList.add('accordion-open')
        button.classList.remove('accordion-closed')
    }
}

let button_pressed = document.querySelector('.button-pressed')
let footer_buttons = document.querySelectorAll('.pld-form-footer button')

footer_buttons.forEach(button => {
    button.addEventListener('click', function(){
        button_pressed.value = this.value
    })
})


function updateSpecificHandlerCheckbox() {
  let specificHandlerField = this
  let specificHandlerCheckbox = this.parentElement.parentElement.parentElement
    .querySelector('[id*="-specific_handler_is_excluded"]');

  if (!$(specificHandlerField).val()) {
    specificHandlerCheckbox.checked = false;
    $(specificHandlerCheckbox.parentElement).addClass('off');
    $(specificHandlerCheckbox).trigger('change');
    $(specificHandlerCheckbox.parentElement).addClass('disabled');
  } else {
    $(specificHandlerCheckbox.parentElement).removeClass('disabled');
  }
}


function categoryUpdate() {
  /**
   *  Update unit list to prevent selection of unit-based application method for fixed fees.
   *  Update and lock Hookup Method field if fee category applies to over-wing fuelling only.
   */
  let uomFields = document.querySelectorAll('[id$="_unit"]');
  let hookupField = document.querySelector('[id$="-specific_hookup_method"]');

  uomFields.forEach((uomField) =>{
    if ('data-fixed-uom-only' in $(this).select2('data')[0].element.attributes) {
      uomField.querySelectorAll('option').forEach((el) => {
        if (!el.attributes['data-fixed-uom']) {
          el.disabled = true;
        }
      });
      $(uomField).select2('data').forEach((el) => {
        if (!el.element.attributes['data-fixed-uom']) {
          $(uomField).val(null);
          $(uomField).trigger('change');
        }
      })
    } else {
      uomField.querySelectorAll('option').forEach((el) => {
        el.disabled = false;
      });
    }
  });

  if ('data-overwing-only' in $(this).select2('data')[0].element.attributes) {
    $(hookupField).val('OW');
    $(hookupField).trigger('change');
    hookupField.setAttribute('readonly', true);
  } else {
    hookupField.removeAttribute('readonly');
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

import './includes/_fee_validity_periods.js';
import './includes/_supplier_exchange_rate.js';
