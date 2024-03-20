let form_sections = document.querySelectorAll('.form-section')

let airport_fields = document.querySelectorAll('[name*="exception_airport"]')
let country_fields = document.querySelectorAll('[name*="exception_country"]')

airport_fields.forEach(field => {
    let form_number = getFormNumber(field)
    $(field).on('select2:select', () => {
        $(country_fields[form_number]).val('').trigger('change')
    })

})

country_fields.forEach(field => {
    let form_number = getFormNumber(field)
    $(field).on('select2:select', () => {
        $(airport_fields[form_number]).val('').trigger('change')
    })

})


let tax_form_hidden_divs = document.querySelectorAll('.new-tax-row')
let tax_form_existing_divs = document.querySelectorAll('.existing-tax')
let tax_existing_fields = document.querySelectorAll('[name*="tax_instance"]')

let create_tax_buttons = document.querySelectorAll('.new-tax-button')
let new_tax_text = document.querySelectorAll('.new-tax-text')
let new_tax_icon = document.querySelectorAll('.new-tax-icon')

create_tax_buttons.forEach(button => {
    let form_number = getFormNumber(button)
    let new_tax_fields = document.querySelectorAll(`[name*="${form_number}-category"], [name*="${form_number}-local_name"], [name*="${form_number}-short_name"]`)
    let required_tax_fields = document.querySelectorAll(`[name*="${form_number}-category"], [name*="${form_number}-local_name"]`)

    has_existing_tax = false
    new_tax_fields.forEach(field => {

        if (field.value != ''){

            tax_form_existing_divs[form_number].classList.add('d-none')
            alterFieldRequirements(tax_existing_fields[form_number], action='remove')
            tax_form_hidden_divs[form_number].classList.remove('d-none')
            alterFieldRequirements(required_tax_fields, action='add')

            new_tax_text[form_number].innerHTML = 'Pick an Existing Tax'
            new_tax_icon[form_number].classList.remove('fa-plus', 'text-success')
            new_tax_icon[form_number].classList.add('fa-minus', 'text-danger')

        }
    })

    button.addEventListener('click', () => {
        let form_number = getFormNumber(button)
        let required_tax_fields = document.querySelectorAll(`[name*="${form_number}-category"], [name*="${form_number}-local_name"]`)
        let new_tax_fields = document.querySelectorAll(`[name*="${form_number}-category"], [name*="${form_number}-local_name"], [name*="${form_number}-short_name"]`)


        if (tax_form_hidden_divs[form_number].classList.contains('d-none')){

            tax_form_existing_divs[form_number].classList.add('d-none')
            alterFieldRequirements(tax_existing_fields[form_number], action='remove')
            tax_form_hidden_divs[form_number].classList.remove('d-none')
            alterFieldRequirements(required_tax_fields, action='add')

            new_tax_text[form_number].innerHTML = 'Pick an Existing Tax'
            new_tax_icon[form_number].classList.remove('fa-plus', 'text-success')
            new_tax_icon[form_number].classList.add('fa-minus', 'text-danger')

        } else {

            tax_form_existing_divs[form_number].classList.remove('d-none')
            alterFieldRequirements(tax_existing_fields[form_number], action='add')
            tax_form_hidden_divs[form_number].classList.add('d-none')
            alterFieldRequirements(required_tax_fields, action='remove')

            new_tax_text[form_number].innerHTML = 'Add New Tax Definition'
            new_tax_icon[form_number].classList.remove('fa-minus', 'text-danger')
            new_tax_icon[form_number].classList.add('fa-plus', 'text-success')
        }
        $(tax_existing_fields[form_number]).val('').trigger('change')
        new_tax_fields.forEach(field => {
            $(field).val('').trigger('change')
        })

    })
})

tax_existing_fields.forEach(field => {
    let form_number = getFormNumber(field)
    if(!form_sections[form_number].classList.contains('d-none') && !field.parentElement.parentElement.classList.contains('d-none')){
        alterFieldRequirements(field, action='add')
    }

})

function alterFieldRequirements(fields, action){
    if(!isNodeList(fields)){
        let field = fields
        let label = field.previousElementSibling


        if(action == 'add'){
            field.setAttribute('required', "")
            if(label != null){
                label.nodeName == 'LABEL' ? label.classList.add('required') : ''
            }
        } else {
            field.removeAttribute('required')
            if(label != null){
                label.nodeName == 'LABEL' ? label.classList.remove('required') : ''
            }
        }
    } else {
        fields.forEach(field => {
            let label = field.previousElementSibling

            if(action == 'add'){
                field.required = true
                if(label != null){
                    label.nodeName == 'LABEL' ? label.classList.add('required') : ''
                }
            } else {
                field.required = false
                if(label != null){
                    label.nodeName == 'LABEL' ? label.classList.remove('required') : ''
                }
            }
        })
    }
}

let specific_fuel_fields = document.querySelectorAll('[name$="specific_fuel"]')
let specific_fuel_cat_fields = document.querySelectorAll('[name$="specific_fuel_cat"]')
let specific_fee_category_fields = document.querySelectorAll('[name*="specific_fee_category"]')

specific_fuel_fields.forEach(field => {
    let form_number = getFormNumber(field)
    $(field).on('select2:select', () => {
        $(specific_fuel_cat_fields[form_number]).val('').trigger('change');
        specific_fuel_cat_fields[form_number].disabled = true;
    })

    $(field).on('select2:clear', () => {
      specific_fuel_cat_fields[form_number].disabled = false;
    })
})

specific_fuel_cat_fields.forEach(field => {
    let form_number = getFormNumber(field)
    $(field).on('select2:select', () => {
        $(specific_fuel_fields[form_number]).val('').trigger('change');
        specific_fuel_fields[form_number].disabled = true;
    })

    $(field).on('select2:clear', () => {
      specific_fuel_fields[form_number].disabled = false;
    })
})

let fuel_checkboxes = document.querySelectorAll('[name*="applies_to_fuel"]')
let service_checkboxes = document.querySelectorAll('[name*="applies_to_fees"]')

fuel_checkboxes.forEach(checkbox => {

    let form_number = getFormNumber(checkbox)
    alterFieldOnCheckboxChange(checkbox, specific_fuel_fields, form_number, specific_fuel_cat_fields)
    alterFieldOnCheckboxChange(checkbox, specific_fuel_cat_fields, form_number, specific_fuel_fields)

    checkbox.addEventListener('change', () => {
        alterFieldOnCheckboxChange(checkbox, specific_fuel_fields, form_number, specific_fuel_cat_fields)
        alterFieldOnCheckboxChange(checkbox, specific_fuel_cat_fields, form_number, specific_fuel_fields)

        if(!checkbox.checked && !service_checkboxes[form_number].checked){
            service_checkboxes[form_number].checked = true
            specific_fuel_fields[form_number].disabled = true
            specific_fuel_cat_fields[form_number].disabled = true
            specific_fee_category_fields[form_number].disabled = false
        }
    })
})

service_checkboxes.forEach(checkbox => {

    let form_number = getFormNumber(checkbox)
    alterFieldOnCheckboxChange(checkbox, specific_fee_category_fields, form_number)

    checkbox.addEventListener('change', () => {
        alterFieldOnCheckboxChange(checkbox, specific_fee_category_fields, form_number)

        if(!checkbox.checked && !fuel_checkboxes[form_number].checked){
            fuel_checkboxes[form_number].checked = true
            specific_fuel_fields[form_number].disabled = false
            specific_fuel_cat_fields[form_number].disabled = false
            specific_fee_category_fields[form_number].disabled = true
        }
    })
})

function alterFieldOnCheckboxChange(checkbox, fields, form_number, alternativeFields=null){
    if (checkbox.checked && (!alternativeFields || $(alternativeFields[form_number]).val() === '')){
        fields[form_number].disabled = false
    } else {
        fields[form_number].disabled = true
        $(fields[form_number]).val('').trigger('change')
    }
}


let private_checkboxes = document.querySelectorAll('[name*="applies_to_private"]')
let commercial_checkboxes = document.querySelectorAll('[name*="applies_to_commercial"]')

private_checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
        let form_number = getFormNumber(checkbox)
        if(!checkbox.checked && !commercial_checkboxes[form_number].checked){
            commercial_checkboxes[form_number].checked = true
        }
    })
})

commercial_checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
        let form_number = getFormNumber(checkbox)
        if(!checkbox.checked && !private_checkboxes[form_number].checked){
            private_checkboxes[form_number].checked = true
        }
    })
})

let official_taxable_checkboxes = document.querySelectorAll('[name*="taxed_by_vat"]')
let exception_taxable_checkboxes = document.querySelectorAll('[name*="taxed_by_exception"]')
let official_taxable_divs = document.querySelectorAll('.taxable-taxes')
let exception_taxable_divs = document.querySelectorAll('.taxable-exceptions')
let official_taxable_fields = document.querySelectorAll('[name*="taxable_tax"]')
let exception_taxable_fields = document.querySelectorAll('[name*="taxable_exception"]')

official_taxable_checkboxes.forEach(checkbox => {
    let form_number = getFormNumber(checkbox)
    alterVisibilityOnCheckboxChange(checkbox, official_taxable_divs[form_number], official_taxable_fields[form_number])

    checkbox.addEventListener('change', () => {
        alterVisibilityOnCheckboxChange(checkbox, official_taxable_divs[form_number], official_taxable_fields[form_number])
    })
})

exception_taxable_checkboxes.forEach(checkbox => {
    let form_number = getFormNumber(checkbox)
    alterVisibilityOnCheckboxChange(checkbox, exception_taxable_divs[form_number], exception_taxable_fields[form_number])

    checkbox.addEventListener('change', () => {
        alterVisibilityOnCheckboxChange(checkbox, exception_taxable_divs[form_number], exception_taxable_fields[form_number])
    })
})


function alterVisibilityOnCheckboxChange(checkbox, div, field){

    if(checkbox.checked){
        div.classList.remove('d-none')
        alterRequiredFieldAttribute(field, 'add')

    } else {
        div.classList.add('d-none')
        alterRequiredFieldAttribute(field, 'remove')
    }

}

function alterRequiredFieldAttribute(field, action, skip_label=false){
    let label = field.previousElementSibling

    if(action == 'add'){
        field.required = true
        if(!skip_label){
            label.classList.add('required')
        }
    } else {
        field.required = false
        label.classList.remove('required')
        $(field).val('').trigger('change')
    }

}

let flight_type_fields = document.querySelectorAll('[name*="applicable_flight_type"]')
let geographic_flight_type_fields = document.querySelectorAll('[name*="geographic_flight_type"]')
let valid_from_fields = document.querySelectorAll('[name*="valid_from"]')

let core_fields = [...flight_type_fields, ...geographic_flight_type_fields, ...valid_from_fields]


core_fields.forEach(field => {
    let form_number = getFormNumber(field)

    if(!form_sections[form_number].classList.contains('d-none')){
        alterRequiredFieldAttribute(field, 'add', true)
    }
})


charging_method_fields = document.querySelectorAll('[name*="charging_method"]')

application_method_fields = document.querySelectorAll('[name*="application_method"]')
fuel_application_method_fields = document.querySelectorAll('[name*="fuel_pricing_unit"]')
application_method_divs = document.querySelectorAll('.application-method')
fuel_application_method_divs = document.querySelectorAll('.fuel-application-method')

percentage_fields = document.querySelectorAll('[name*="tax_percentage"]')
flat_amount_fields = document.querySelectorAll('[name*="tax_unit_rate"]')
percentage_divs = document.querySelectorAll('.percentage-rate')
flat_amount_divs = document.querySelectorAll('.fixed-rate')

band_pricing_fields = document.querySelectorAll('[name$="band_pricing_amount"]')

condition_one_fields = document.querySelectorAll('[name*="band_1_type"]')
condition_two_fields = document.querySelectorAll('[name*="band_2_type"]')


$(document).ready(function(){

    setTimeout(() => {
        reInitializeOfficialTaxField()
        reInitializeExceptionTaxField()
    }, 300)

    charging_method_fields.forEach(field => {
        let form_number = getFormNumber(field)
        showAppropriateChargeFields($(field).select2('data')[0].text, form_number, getFormChargingMethod(form_number))
        $(field).on('select2:select', function () {
            showAppropriateChargeFields($(field).select2('data')[0].text, form_number, getFormChargingMethod(form_number))
        })
    })

    condition_one_fields.forEach(field => {
        let form_number = getFormNumber(field)
        showAppropriateChargeFields(getCurrentChargingMethod(form_number), form_number, getFormChargingMethod(form_number))

        let condition_one_fields = document.querySelectorAll(`[name*="${form_number}-band_1_start"], [name*="${form_number}-band_1_end"]`)
        if ($(field).val() != ''){
            alterFieldRequirements(condition_one_fields, 'add')
        }

        $(field).on('select2:select', () => {
            showAppropriateChargeFields(getCurrentChargingMethod(form_number), form_number, getFormChargingMethod(form_number))
            alterFieldRequirements(condition_one_fields, 'add')
        })
        $(field).on('select2:clear', () => {
            showAppropriateChargeFields(getCurrentChargingMethod(form_number), form_number, getFormChargingMethod(form_number))
            alterFieldRequirements(condition_one_fields, 'remove')
        })
    })

    condition_two_fields.forEach(field => {
        let form_number = getFormNumber(field)
        showAppropriateChargeFields(getCurrentChargingMethod(form_number), form_number, getFormChargingMethod(form_number))

        let condition_two_fields = document.querySelectorAll(`[name*="${form_number}-band_2_start"], [name*="${form_number}-band_2_end"]`)
        if ($(field).val() != ''){
            alterFieldRequirements(condition_two_fields, 'add')
        }
        $(field).on('select2:select', () => {
            showAppropriateChargeFields(getCurrentChargingMethod(form_number), form_number, getFormChargingMethod(form_number))
            alterFieldRequirements(condition_two_fields, 'add')
        })
        $(field).on('select2:clear', () => {
            showAppropriateChargeFields(getCurrentChargingMethod(form_number), form_number, getFormChargingMethod(form_number))
            alterFieldRequirements(condition_two_fields, 'remove')
        })
    })
})

function showAppropriateChargeFields(charging_method, form_number, form_type){

    if(form_sections[form_number].classList.contains('d-none')){
        return
    }

    let band_pricing_label = band_pricing_fields[form_number].previousElementSibling
    let band_pricing_div = band_pricing_fields[form_number].parentElement.parentElement

    if(charging_method == 'Percentage of Net Price'){

        alterRequiredFieldAttribute(percentage_fields[form_number], 'add')
        alterRequiredFieldAttribute(flat_amount_fields[form_number], 'remove')

        $(application_method_fields[form_number]).val('').trigger('change')
        $(fuel_application_method_fields[form_number]).val('').trigger('change')

        fuel_application_method_fields[form_number].disabled = true
        application_method_fields[form_number].disabled = true
        alterFieldRequirements(fuel_application_method_fields[form_number], 'remove')
        alterFieldRequirements(application_method_fields[form_number], 'remove')

        if(form_type == 'default'){
            flat_amount_divs[form_number].classList.add('d-none')
            percentage_divs[form_number].classList.remove('d-none')

            percentage_fields[form_number].disabled = false
            flat_amount_fields[form_number].value = ''

            band_pricing_div.classList.add('d-none')
            alterFieldRequirements(band_pricing_fields[form_number], 'remove')
            band_pricing_fields[form_number].value = ''
            band_pricing_fields[form_number].disabled = true
        } else {
            initializeBandPricing(charging_method, form_number)
        }

    } else if (charging_method == 'Fixed Cost'){

        alterRequiredFieldAttribute(percentage_fields[form_number], 'remove')
        alterRequiredFieldAttribute(flat_amount_fields[form_number], 'add')

        $(fuel_application_method_fields[form_number]).val('').trigger('change')

        fuel_application_method_fields[form_number].disabled = true
        application_method_fields[form_number].disabled = false
        alterFieldRequirements(fuel_application_method_fields[form_number], 'remove')
        alterFieldRequirements(application_method_fields[form_number], 'add')

        fuel_application_method_divs[form_number].classList.add('d-none')
        application_method_divs[form_number].classList.remove('d-none')

        if(form_type == 'default'){
            flat_amount_divs[form_number].classList.remove('d-none')
            percentage_divs[form_number].classList.add('d-none')

            flat_amount_fields[form_number].disabled = false
            percentage_fields[form_number].value = ''

            band_pricing_div.classList.add('d-none')
            alterFieldRequirements(band_pricing_fields[form_number], 'remove')
            band_pricing_fields[form_number].value = ''
            band_pricing_fields[form_number].disabled = true
        } else {
            initializeBandPricing(charging_method, form_number)
        }

    } else if (charging_method == 'Fixed Cost (Fuel Based)'){

        alterRequiredFieldAttribute(percentage_fields[form_number], 'remove')
        alterRequiredFieldAttribute(flat_amount_fields[form_number], 'add')

        $(application_method_fields[form_number]).val('').trigger('change')

        fuel_application_method_fields[form_number].disabled = false
        application_method_fields[form_number].disabled = true
        alterFieldRequirements(fuel_application_method_fields[form_number], 'add')
        alterFieldRequirements(application_method_fields[form_number], 'remove')

        fuel_application_method_divs[form_number].classList.remove('d-none')
        application_method_divs[form_number].classList.add('d-none')

        if(form_type == 'default'){
            flat_amount_divs[form_number].classList.remove('d-none')
            percentage_divs[form_number].classList.add('d-none')

            flat_amount_fields[form_number].disabled = false
            percentage_fields[form_number].value = ''

            band_pricing_div.classList.add('d-none')
            alterFieldRequirements(band_pricing_fields[form_number], 'remove')
            band_pricing_fields[form_number].value = ''
            band_pricing_fields[form_number].disabled = true

        } else {
            initializeBandPricing(charging_method, form_number)
        }
    }

}

function initializeBandPricing(charging_method, form_number){

    let band_pricing_label = band_pricing_fields[form_number].previousElementSibling
    let band_pricing_div = band_pricing_fields[form_number].parentElement.parentElement

    if(charging_method == 'Percentage of Net Price'){

        flat_amount_divs[form_number].classList.add('d-none')
        percentage_divs[form_number].classList.add('d-none')

        alterFieldRequirements(percentage_fields[form_number], 'remove')
        percentage_fields[form_number].value = ''
        percentage_fields[form_number].disabled = true

        alterFieldRequirements(flat_amount_fields[form_number], 'remove')
        flat_amount_fields[form_number].value = ''
        flat_amount_fields[form_number].disabled = true

        band_pricing_div.classList.remove('d-none')
        alterFieldRequirements(band_pricing_fields[form_number], 'add')
        band_pricing_fields[form_number].disabled = false
        band_pricing_label.innerHTML = 'Tax Percentage'

    } else if (charging_method == 'Fixed Cost'){

        flat_amount_divs[form_number].classList.add('d-none')
        percentage_divs[form_number].classList.add('d-none')

        alterFieldRequirements(percentage_fields[form_number], 'remove')
        percentage_fields[form_number].value = ''
        percentage_fields[form_number].disabled = true

        alterFieldRequirements(flat_amount_fields[form_number], 'remove')
        flat_amount_fields[form_number].value = ''
        flat_amount_fields[form_number].disabled = true

        band_pricing_div.classList.remove('d-none')
        alterFieldRequirements(band_pricing_fields[form_number], 'add')
        band_pricing_fields[form_number].disabled = false
        band_pricing_label.innerHTML = 'Tax Unit Rate'

    } else if (charging_method == 'Fixed Cost (Fuel Based)'){

        flat_amount_divs[form_number].classList.add('d-none')
        percentage_divs[form_number].classList.add('d-none')

        alterFieldRequirements(percentage_fields[form_number], 'remove')
        percentage_fields[form_number].value = ''
        percentage_fields[form_number].disabled = true
        percentage_divs[form_number].classList.add('d-none')

        alterFieldRequirements(flat_amount_fields[form_number], 'remove')
        flat_amount_fields[form_number].value = ''
        flat_amount_fields[form_number].disabled = true

        band_pricing_div.classList.remove('d-none')
        alterFieldRequirements(band_pricing_fields[form_number], 'add')
        band_pricing_fields[form_number].disabled = false
        band_pricing_label.innerHTML = 'Tax Unit Rate'
    }
}

let add_band_buttons = document.querySelectorAll('.new-band-button')

add_band_buttons.forEach(button => {
    let form_number = getFormNumber(button)
    button.addEventListener('click', () => {
        addBandRow(form_number, button)
    })
})


function addBandRow(form_number, button){
    let band_row = document.querySelectorAll(`#bandAccordion-${form_number} .band-row`)
    initializeBandPricing(getCurrentChargingMethod(form_number), form_number)
    let row_num = band_row.length

    let new_band_row = band_row[row_num-1].cloneNode(true)

    let labels = new_band_row.querySelectorAll('label')
    labels.forEach(label => {
        label.remove()
    })
    let bands = new_band_row.querySelectorAll('input:not([name*="start"])')
    let start_bands = new_band_row.querySelectorAll('[name*="start"]')
    let pricing_field = new_band_row.querySelector('[name*="band_pricing_amount"]')
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

    let insert_before = document.querySelector(`#bandAccordion-${form_number} .insert-before-band`)
    button.parentElement.insertBefore(new_band_row, insert_before)
    new_band_row.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));

    alterBandFieldNumbering(form_number)
    reformatSections()
}

reformatSections()

form_prefix = 'new-tax-rule-exception'

function alterBandFieldNumbering(form_number){
    let band_1_start_fields = document.querySelectorAll(`[name*="${form_number}-band_1_start"]`)
    let band_1_end_fields = document.querySelectorAll(`[name*="${form_number}-band_1_end"]`)
    let band_2_start_fields = document.querySelectorAll(`[name*="${form_number}-band_2_start"]`)
    let band_2_end_fields = document.querySelectorAll(`[name*="${form_number}-band_2_end"]`)
    let band_pricing_fields = document.querySelectorAll(`[name*="${form_number}-band_pricing_amount"]`)

    if(band_1_start_fields.length > 1){
        let i = 0
        band_1_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_number}-band_1_start-additional-${form_number}-${i}`
                field.name = `${form_prefix}-${form_number}-band_1_start-additional-${form_number}-${i}`
            }
            i++
        })

        i = 0
        band_1_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_number}-band_1_end-additional-${form_number}-${i}`
                field.name = `${form_prefix}-${form_number}-band_1_end-additional-${form_number}-${i}`
            }
            i++
        })
        i = 0
        band_2_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_number}-band_2_start-additional-${form_number}-${i}`
                field.name = `${form_prefix}-${form_number}-band_2_start-additional-${form_number}-${i}`
            }
            i++
        })

        i = 0
        band_2_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_number}-band_2_end-additional-${form_number}-${i}`
                field.name = `${form_prefix}-${form_number}-band_2_end-additional-${form_number}-${i}`
            }
            i++
        })

        i = 0
        band_pricing_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_number}-band_pricing_amount-additional-${form_number}-${i}`
                field.name = `${form_prefix}-${form_number}-band_pricing_amount-additional-${form_number}-${i}`
            }
            i++
        })
    }
}

let delete_band_row_buttons = document.querySelectorAll('.delete-row')

delete_band_row_buttons.forEach(button => {
    button.addEventListener('click', function() {
        this.parentElement.parentElement.remove()
    })
})

let default_buttons = document.querySelectorAll('.revert-button')

default_buttons.forEach(button => {
    let form_number = getFormNumber(button)
    button.addEventListener('click', () => {
        revertToDefault(form_number)
    })

})


function revertToDefault(form_number){

    let band_rows = document.querySelectorAll(`#collapseBandAccordion-${form_number} .band-row`)

    let i = 0
    band_rows.forEach(row => {
        if(i > 0){
            row.remove()
        }
        i++
    })


    let band_fields = document.querySelectorAll(`
        #collapseBandAccordion-${form_number} .band-row input
    `)

    let band_1_type_field = document.querySelector(`[name*="${form_number}-band_1_type"]`)
    let band_2_type_field = document.querySelector(`[name$="${form_number}-band_2_type"]`)

    $(band_1_type_field).val('').trigger('change')
    $(band_2_type_field).val('').trigger('change')

    band_fields.forEach(field => {
        field.value = ""
    })

    showAppropriateChargeFields(getCurrentChargingMethod(form_number), form_number, 'default')
    alterFieldRequirements(band_fields, 'remove')
}

let form_section_button = document.querySelector('.add-form-section')
let delete_checkboxes = document.querySelectorAll('[name*=DELETE]')

form_section_button.addEventListener('click', () => {
    for (let index = 0; index < form_sections.length; index++) {
        if(form_sections[index].classList.contains('d-none')){
            form_sections[index].classList.remove('d-none')
            delete_checkboxes[index].checked = false
            showAppropriateChargeFields(getCurrentChargingMethod(index), index, 'default')
            reformatSections()
            break
        }
    }
})

function reformatSections(){
    let header_titles = document.querySelectorAll('.form-section-title')
    let form_sections = document.querySelectorAll('.form-section')

    let i = 1
    header_titles.forEach(title => {
        title.innerHTML = `Tax #${i}`
        i++
    })

    let n = 1
    form_sections.forEach(section => {
        n % 2 == 0 ? section.style.background = '#11182713' : section.style.background = "white"
        n++
    })
}

let delete_buttons = document.querySelectorAll('.delete-form-section')
let visible_sections = document.querySelectorAll('.form-section:not(.d-none)')

delete_buttons.forEach(button => {
    let form_number = getFormNumber(button)
    button.addEventListener('click', () => {
        deleteFormSection(form_number)
    })
})

visible_sections.length == 1 ? delete_buttons[0].disabled = true : ''

function deleteFormSection(form_number){

    let section = document.querySelector(`.form-${form_number}`)
    let visible_sections = document.querySelectorAll('.form-section:not(.d-none)')

    if(visible_sections.length > 1){
        section.classList.add('d-none')
        deleteFormData(section)
    }
}

function deleteFormData(form_section){
    let form_fields = form_section.querySelectorAll('input, select, textarea')
    let delete_field = form_section.querySelector('[name*=DELETE]')
    let fuel_field = form_section.querySelector('[name*="applies_to_fuel"]')
    let private_field = form_section.querySelector('[name*="applies_to_private"]')

    form_fields.forEach(field => {
        if(field != delete_field){
            field.value = ''
            field.checked = false
        }
        field.required = false
        if(field.nodeName == 'SELECT'){
            select_field = $(field)
            select_field.val(null).trigger('change')
        }
        delete_field.checked = true
        fuel_field.checked = true
        private_field.checked = true
    })
}

let accordion_arrows = document.querySelectorAll('.accordion-arrow')
accordion_arrows.forEach(arrow => {
    setAccordionArrow(arrow)

    let accordion_button = arrow.parentElement.parentElement
    accordion_button.addEventListener('click', function(){
        setAccordionArrow(arrow)
    })
})

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


// -- //

function isNodeList(nodes) {
    var stringRepr = Object.prototype.toString.call(nodes);

    return typeof nodes === 'object' &&
        /^\[object (HTMLCollection|NodeList|Object)\]$/.test(stringRepr) &&
        (typeof nodes.length === 'number') &&
        (nodes.length === 0 || (typeof nodes[0] === "object" && nodes[0].nodeType > 0));
}

function getFormNumber(dom_element){
    if (dom_element.id){
        return dom_element.id.match(/\d+/)[0]
    } else {
        let element_with_form_designator = dom_element.closest("[class^='form-']")
        return Array.from(element_with_form_designator.classList).find(className =>
            className.match(/\d+/)).match(/\d+/)[0]
    }
}

function getCurrentChargingMethod(form_number){
    return $(`[name*="${form_number}-charging_method"]`).select2('data')[0].text
}

function getBandOneType(form_number){
    return  $(`[name*="${form_number}-band_1_type"]`).select2('data')[0].text
}

function getBandTwoType(form_number){
    return  $(`[name*="${form_number}-band_2_type"]`).select2('data')[0].text
}

function getFormChargingMethod(form_number){

    let band_rows = document.querySelectorAll(`.form-${form_number} .band-row`)
    let first_row_fields = document.querySelectorAll(`.form-${form_number} .band-row input`)

    first_row_has_data = false
    first_row_fields.forEach(field => {
        if(field.value != ""){
            first_row_has_data = true
        }
    })

    if ((getBandOneType(form_number) != '' || getBandTwoType(form_number) != '' || band_rows.length > 1 || first_row_has_data)){
        return 'band-based'
    } else {
        return 'default'
    }
}


function formatSearch(item) {
    var selectionText = item.text.split("|");
    var $returnString = $('<span>' + selectionText[0] + '</br><b>' + selectionText[1] + '</b></br>' + selectionText[2] +'</br>' + selectionText[3] + '</br><b>' + selectionText[4] + '</b></span>');
    return $returnString;
};

function formatSelected(item) {
    var selectionText = item.text.split("|");
    var $returnString = $('<span>' + selectionText[0] +'</span>');
    return $returnString;
};



function reInitializeOfficialTaxField(){
    $('.django-select2[name*="taxable_tax"]').each(function () {
        $(this).select2("destroy")
        $(this).djangoSelect2({
            dropdownParent: $(this).parent(),
            width: '100%',
            minimumResultsForSearch: 20,
            templateResult: formatSearch,
            templateSelection: formatSelected,
        });
    });
}

function reInitializeExceptionTaxField(){
    $('.django-select2[name*="taxable_exception"]').each(function () {
        $(this).select2("destroy")
        $(this).djangoSelect2({
            dropdownParent: $(this).parent(),
            width: '100%',
            minimumResultsForSearch: 20,
            templateResult: formatSearch,
            templateSelection: formatSelected,
        });
    });
}
