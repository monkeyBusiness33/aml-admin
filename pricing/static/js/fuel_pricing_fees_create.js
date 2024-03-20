import './includes/_fee_validity_periods.js';
import showFinalSupplierExchangeRate from './includes/_supplier_exchange_rate.js';


let categoryFields = document.querySelectorAll('[id$="-fuel_fee_category"]')
let form_instance = document.getElementById('fuel_fee_form')

reformatSections()
toggleDeleteButtonDisabledAttr()
addAllEventListeners()

let accordion_arrows = document.querySelectorAll('.accordion-arrow')
accordion_arrows.forEach(arrow => {
    setAccordionArrow(arrow)

    let accordion_button = arrow.parentElement.parentElement
    accordion_button.addEventListener('click', function(){
        setAccordionArrow(arrow)
    })
})

$(document).ready(function(){
    let band_type_fields = $(`[name*="band_uom"]`)
    let weight_band_type_fields = $(`[name$="weight_band"]`)
    initializeBandPricing(weight_band_type_fields)
    initializeBandPricing(band_type_fields)

    $(categoryFields).trigger('change');
})


function addAllEventListeners(){
    let add_section_buttons = document.querySelectorAll('.add-form-section')
    let delete_section_buttons = document.querySelectorAll('.delete-form-section')
    let add_band_buttons = document.querySelectorAll('.new-band-button')
    let delete_band_buttons = document.querySelectorAll('.delete-row')
    let band_type_fields = $(`[name*="band_uom"]`)
    let weight_band_type_fields = $(`[name$="weight_band"]`)
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

    document.querySelectorAll('input[id*="-specific_handler_is_excluded"]').forEach((handlerToggle) => {
      waitForElement(`.toggle-group [for*="${handlerToggle.id}"]`).then((el) => {
        let handlerField = handlerToggle.closest('.location-row').querySelector('select[id*="-specific_handler"]')
        $(handlerField).on('change', updateSpecificHandlerCheckbox);
        // Update fields for all already shown forms on load
        $(handlerField).trigger('change');
      });
    });

    $(categoryFields).on('change', categoryUpdate);
}


function revertToDefault(){
    let form_num = this.parentElement.id.match(/\d+/)[0]

    let band_rows = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row`)
    let band_pricing_field = document.querySelector(`#id_new-fuel-fee-rate-${form_num}-band_pricing_native_amount`)
    let form_pricing_fields = document.querySelectorAll(`[name*="${form_num}-pricing_native_amount"]`)

    let i = 0
    band_rows.forEach(row => {
        if(i > 0){
            row.remove()
        }
        i++
    })

    band_pricing_field.required = false
    band_pricing_field.parentElement.parentElement.classList.add('d-none')



    form_pricing_fields.forEach(field => {
        field.required = true
        field.parentElement.parentElement.classList.remove('d-none')
    })

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

    let band_labels = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row label`)
    band_labels.forEach(label => {
        label.classList.remove('required')
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


function alterBandPricing(band_field){

    let selected_data = band_field.select2('data')[0].text
    let field = document.getElementById(band_field.attr('id'))
    let form_num = field.id.match(/\d+/)[0]
    let band_rows = document.querySelectorAll(`#collapseBandAccordion-${form_num} .band-row`)

    if(selected_data != "" && selected_data != "---------"){

        alterAmountField(form_num, 'add')
        alterRequiredAttribute(band_field, form_num, 'add')

    } else if (selected_data == "" && band_rows.length == 1) {
        // Can't trigger this as we don't have the clear field for some reason

        alterRequiredAttribute(band_field, form_num, 'remove')
    }
}


function alterAmountField(form_num, action){
    let band_pricing_field = document.querySelector(`#id_new-fuel-fee-rate-${form_num}-band_pricing_native_amount`)
    let form_pricing_fields = document.querySelectorAll(`[name*="${form_num}-pricing_native_amount"]`)
    let band_pricing_label = document.querySelector(`#collapseBandAccordion-${form_num} .band-row [for*="band_pricing_native"]`)

    if(action == 'add'){
        band_pricing_field.required = true
        band_pricing_field.parentElement.parentElement.classList.remove('d-none')
        band_pricing_label.classList.add('required')

        form_pricing_fields.forEach(field => {
            field.value = ''
            field.required = false
            field.parentElement.parentElement.classList.add('d-none')
        })

    } else {
        band_pricing_field.required = false
        band_pricing_field.parentElement.parentElement.classList.add('d-none')
        band_pricing_label.classList.remove('required')
        band_pricing_field.value = ''

        form_pricing_fields.forEach(field => {
            field.required = true
            field.parentElement.parentElement.classList.remove('d-none')
        })

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
                field.id = `id_new-fuel-fee-rate-${form_num}-quantity_band_start-additional-${form_num}-${i}`
                field.name = `new-fuel-fee-rate-${form_num}-quantity_band_start-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        band_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_new-fuel-fee-rate-${form_num}-quantity_band_end-additional-${form_num}-${i}`
                field.name = `new-fuel-fee-rate-${form_num}-quantity_band_end-additional-${form_num}-${i}`
            }
            i++
        })
        i = 0
        weight_band_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_new-fuel-fee-rate-${form_num}-weight_band_start-additional-${form_num}-${i}`
                field.name = `new-fuel-fee-rate-${form_num}-weight_band_start-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        weight_band_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_new-fuel-fee-rate-${form_num}-weight_band_end-additional-${form_num}-${i}`
                field.name = `new-fuel-fee-rate-${form_num}-weight_band_end-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        band_pricing_fields.forEach(field => {
            if(i > 0){
                field.id = `id_new-fuel-fee-rate-${form_num}-band_pricing_native_amount-additional-${form_num}-${i}`
                field.name = `new-fuel-fee-rate-${form_num}-band_pricing_native_amount-additional-${form_num}-${i}`
            }
            i++
        })
    }
}


function addFormSection(){

    let form_sections = document.querySelectorAll('.d-none.form-section')
    form_sections[0].classList.remove('d-none')
    let delete_fields = form_sections[0].querySelectorAll('[name*="DELETE"]')
    delete_fields.forEach(field => {
        field.checked = false
    })

    toggleDeleteButtonDisabledAttr()

    }

function alterFormSectionInput(form_section, action){
    let form_fields = form_section.querySelectorAll('input, select, textarea')
    let delete_fields = form_section.querySelectorAll('[name*="DELETE"]')

    if(action == 'delete'){
        form_fields.forEach(field => {
            if (field != delete_fields[0] && field != delete_fields[1]){
                field.value = ''
                field.required = false
            }
            if(field.nodeName == 'SELECT'){
                let select_field = $(field)
                select_field.val(null).trigger('change')
            }
        })
        delete_fields.forEach(field => {
            field.checked = true
        })
    }
}


function toggleDeleteButtonDisabledAttr(){
    let form_sections = document.querySelectorAll('.form-section:not(.d-none)')
    let delete_section_buttons = document.querySelectorAll('.delete-form-section')

    if(form_sections.length == 1){
        delete_section_buttons[0].disabled = true
    } else {
        delete_section_buttons.forEach(button => {
            button.disabled = false
        })
    }
}


function deleteFormSection(){

    let form_sections = document.querySelectorAll('.form-section:not(.d-none)')
    let delete_section_buttons = document.querySelectorAll('.delete-form-section')

    if(form_sections.length > 1){
        this.parentElement.parentElement.parentElement.classList.add('d-none')
        alterFormSectionInput(this.parentElement.parentElement.parentElement, 'delete')
    }

    if(form_sections.length == 2){
        delete_section_buttons[0].disabled = true
    } else {
        delete_section_buttons[0].disabled = false
    }
}


function reformatSections(){
    let header_titles = document.querySelectorAll('.form-section-title')
    let form_sections = document.querySelectorAll('.fuel-form-body')

    let i = 1
    header_titles.forEach(title => {
        title.innerHTML = `Fee #${i}`
        i++
    })

    let n = 1
    form_sections.forEach(section => {
        n % 2 == 0 ? section.style.background = '#11182713' : section.style.background = "white"
        n++
    })
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
        if (this.value == 'skip'){
            let form_fields = document.querySelectorAll('select, textarea, input')
            form_fields.forEach(field => {
                field.required = false
            })
        }
    })
})

let new_row_buttons = document.querySelectorAll('.new-row-button')

new_row_buttons.forEach(button => {
    button.addEventListener('click', addNewFeeRow)
})


function addNewFeeRow(){
    let form_num = this.parentElement.id.match(/\d+/)[0]
    let insert_before = this.parentElement.querySelector('.insert-before-row')
    let location_fields = document.querySelectorAll(`[name*="${form_num}-location-additional"]`)
    let last_field_number = location_fields.length > 1
      ? location_fields[location_fields.length-1].name.match(/additional-\d/gm)[0].split('-')[1]
      : 0;

    let new_field_number

    if(parseInt(last_field_number) >= location_fields.length + 1){
      new_field_number = parseInt(last_field_number)+ 1
    } else {
      new_field_number = location_fields.length + 1
    }

    fetch("", {
        method: 'POST',
        body: JSON.stringify({
          form_number: form_num,
          new_field_number: new_field_number
        }),
        headers: {
            "Content-Type": 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            "X-CSRFToken": getCookie("csrftoken"),
        }
    })
    .then(response => response.text())
    .then(data => {
        let new_div = document.createElement('div')
        new_div.classList.add('row', 'location-row')
        new_div.innerHTML = data
        this.parentElement.insertBefore(new_div, insert_before)
        alterFeeFieldNumbering(form_num, new_field_number, true)
        addDeleteRowEventListener(form_num)

        let handlerField = new_div.querySelector('select[id*="-specific_handler"]');
        $(handlerField).on('change', updateSpecificHandlerCheckbox);
        $(handlerField).trigger('change');
        $(this.closest('.form-section').querySelector('[id$="-fuel_fee_category"]')).trigger('change');

        // Also add the event listener to display total supplier exchange rate
        $(new_div.querySelector('[id*="-pricing_native_unit"]')).on('change', () => showFinalSupplierExchangeRate(form_num));

        new_div.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));
    })
}

function alterFeeFieldNumbering(form_num, new_field_number, last_only){

    let location_fields = document.querySelectorAll(`#locationAccordion-${form_num} .fee-location select`)
    let ipa_fields = document.querySelectorAll(`#locationAccordion-${form_num} .fee-ipa select`)
    let method_fields = document.querySelectorAll(`#locationAccordion-${form_num} .fee-method select`)
    let amount_fields = document.querySelectorAll(`#locationAccordion-${form_num} .fee-amount input`)

    let handler_fields = document.querySelectorAll(`#locationAccordion-${form_num} .fee-specific_handler select`);
    let handler_toggles = document.querySelectorAll(`#locationAccordion-${form_num} .fee-specific_handler_is_excluded input`);
    let apron_fields = document.querySelectorAll(`#locationAccordion-${form_num} .fee-specific_apron select`);

    let row = location_fields.length - 1

    if(last_only){
      location_fields[row].id = `id_new-fuel-fee-rate-${form_num}-location-additional-${new_field_number}`
      location_fields[row].name = `new-fuel-fee-rate-${form_num}-location-additional-${new_field_number}`
      reInitializeFeeFields(location_fields[row].name)

      ipa_fields[row].id = `id_new-fuel-fee-rate-${form_num}-ipa-additional-${new_field_number}`
      ipa_fields[row].name = `new-fuel-fee-rate-${form_num}-ipa-additional-${new_field_number}`
      $(ipa_fields[row]).attr("data-select2-dependent-fields", `new-fuel-fee-rate-${form_num}-location-additional-${new_field_number}`)
      reInitializeFeeFields(ipa_fields[row].name)

      method_fields[row].id = `id_new-fuel-fee-rate-${form_num}-pricing_native_unit-additional-${new_field_number}`
      method_fields[row].name = `new-fuel-fee-rate-${form_num}-pricing_native_unit-additional-${new_field_number}`
      reInitializeFeeFields(method_fields[row].name)

      amount_fields[row].id = `id_new-fuel-fee-rate-${form_num}-pricing_native_amount-additional-${new_field_number}`
      amount_fields[row].name = `new-fuel-fee-rate-${form_num}-pricing_native_amount-additional-${new_field_number}`
      reInitializeFeeFields(amount_fields[row].name)

      handler_fields[row].id = `id_new-fuel-fee-rate-${form_num}-specific_handler-additional-${new_field_number}`
      handler_fields[row].name = `new-fuel-fee-rate-${form_num}-specific_handler-additional-${new_field_number}`
      $(handler_fields[row]).attr("data-select2-dependent-fields", `new-fuel-fee-rate-${form_num}-location-additional-${new_field_number}`)
      reInitializeFeeFields(handler_fields[row].name)

      handler_toggles[row].id = `id_new-fuel-fee-rate-${form_num}-specific_handler_is_excluded-additional-${new_field_number}`
      handler_toggles[row].name = `new-fuel-fee-rate-${form_num}-specific_handler_is_excluded-additional-${new_field_number}`
      $(handler_toggles[row]).bootstrapToggle();

      apron_fields[row].id = `id_new-fuel-fee-rate-${form_num}-specific_apron-additional-${new_field_number}`
      apron_fields[row].name = `new-fuel-fee-rate-${form_num}-specific_apron-additional-${new_field_number}`
      reInitializeFeeFields(apron_fields[row].name)

    } else {
      let i = 1
      location_fields.forEach(field => {
          field.id = `id_new-fuel-fee-rate-${form_num}-location-additional-${i}`
          field.name = `new-fuel-fee-rate-${form_num}-location-additional-${i}`
          reInitializeFeeFields(field.name)
          i++
      })

      i = 1
      ipa_fields.forEach(field => {
          field.id = `id_new-fuel-fee-rate-${form_num}-ipa-additional-${i}`
          field.name = `new-fuel-fee-rate-${form_num}-ipa-additional-${i}`
          $(field).attr("data-select2-dependent-fields", `new-fuel-fee-rate-${form_num}-location-additional-${i}`)
          reInitializeFeeFields(field.name)
          i++
      })
      i = 1
      method_fields.forEach(field => {
          field.id = `id_new-fuel-fee-rate-${form_num}-pricing_native_unit-additional-${i}`
          field.name = `new-fuel-fee-rate-${form_num}-pricing_native_unit-additional-${i}`
          reInitializeFeeFields(field.name)
          i++
      })

      i = 1
      amount_fields.forEach(field => {
          field.id = `id_new-fuel-fee-rate-${form_num}-pricing_native_amount-additional-${i}`
          field.name = `new-fuel-fee-rate-${form_num}-pricing_native_amount-additional-${i}`
          i++
      })

      i = 1
      handler_fields.forEach(field => {
          field.id = `id_new-fuel-fee-rate-${form_num}-specific_handler-additional-${i}`
          field.name = `new-fuel-fee-rate-${form_num}-specific_handler-additional-${i}`
          i++
      })

      i = 1
      handler_toggles.forEach(field => {
          field.id = `id_new-fuel-fee-rate-${form_num}-specific_handler_is_excluded-additional-${i}`
          field.name = `new-fuel-fee-rate-${form_num}-specific_handler_is_excluded-additional-${i}`
          i++
      })

      i = 1
      apron_fields.forEach(field => {
          field.id = `id_new-fuel-fee-rate-${form_num}-specific_apron-additional-${i}`
          field.name = `new-fuel-fee-rate-${form_num}-specific_apron-additional-${i}`
          i++
      })
    }


}

function reInitializeFeeFields(name){
    $('.django-select2').each(function () {
        if($(this).attr('name').includes(name)){
            $(this).djangoSelect2({
                    dropdownParent: $(this).parent(),
                    width: '100%',
                });
        }

    });
}

addDeleteRowEventListener()

function addDeleteRowEventListener(form_num){

    let delete_location_buttons = document.querySelectorAll('.delete-location-row')

    delete_location_buttons.forEach(button => {

      button.addEventListener('click', () => {
        let supplierXRField = button.closest('form').querySelector(`[id*="-supplier_exchange_rate"]`);
        $(supplierXRField).trigger('change');
        button.parentElement.parentElement.remove()
      })
    })
}

let submit_button = document.querySelector('.submit')
submit_button.addEventListener('click', () => {
  for (let index = 0; index < 10; index++) {
    alterFeeFieldNumbering(index, 0, false)

  }
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
  let uomFields = this.closest('.form-section')
    .querySelectorAll('select[id*="pricing_native_unit"], select[id$="pricing_converted_unit"]');
  let hookupFields = this.closest('.form-section').querySelectorAll('[id$="-specific_hookup_method"]');

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

  hookupFields.forEach((hookupField) => {
    if ('data-overwing-only' in $(this).select2('data')[0].element.attributes) {
      $(hookupField).val('OW');
      $(hookupField).trigger('change');
      hookupField.setAttribute('readonly', true);
    } else {
      hookupField.removeAttribute('readonly');
    }
  });
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
