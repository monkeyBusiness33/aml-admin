form_prefix = "tax-rule-exception"

$(document).ready(() => {
    if(!$('#sidebarMenu').hasClass('contracted')){
        $('#sidebar-toggle').click()
    }

    let notification_modal = document.getElementById('notificationModal')
    if (notification_modal){
        $(notification_modal).modal('show')
    }

    setAllDates()

    charging_method_fields = document.querySelectorAll('[name*="charging_method"]')

    charging_method_fields.forEach(field => {
        let form_number = getFormNumber(field)
        showAppropriateChargeFields($(field).select2('data')[0].text, form_number)
        $(field).on('select2:select', function () {
            showAppropriateChargeFields($(field).select2('data')[0].text, form_number)
        })
    })

    let specific_fuel_fields = document.querySelectorAll('[name$="specific_fuel"]')
    let specific_fuel_cat_fields = document.querySelectorAll('[name$="specific_fuel_cat"]')

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
})

let band_1_type_fields = document.querySelectorAll(`[name*="band_1_type"]`)
band_1_type_fields.forEach(field => {
    toggleBandPricing(field)
})

band_1_type_fields.forEach(field => {
    $(field).on('select2:select', function() {
        toggleBandPricing(field)
    })
    $(field).on('select2:clear', function(){
        toggleBandPricing(field)
    })
})

let band_2_type_fields = document.querySelectorAll(`[name$="band_2_type"]`)
band_2_type_fields.forEach(field => {
    toggleBandPricing(field)
})

band_2_type_fields.forEach(field => {
    $(field).on('select2:select', function() {
        toggleBandPricing(field)
    })
    $(field).on('select2:clear', function(){
        toggleBandPricing(field)
    })
})


let form_row = document.querySelectorAll('.form-row.main')

let hide_row_buttons = document.querySelectorAll('.hide-row, .new-hide-row')
let no_change_checkbox = document.querySelectorAll('[id*="no_change"]')

hide_row_buttons.forEach(button => {
    row_number = button.value
    let delete_checkbox = document.querySelector(`.form-${row_number}.main [id*="DELETE"]`)
    let error_mark = button.nextElementSibling

    if(delete_checkbox.checked && error_mark == undefined){
        button.setAttribute('data-bs-target', '')
        alterRowStatus(button)
    } else {
        delete_checkbox.checked = false
    }
})

no_change_checkbox.forEach(button => {
    if(button.checked){
        alterRowStatus(button)
    }
})

hide_row_buttons.forEach(button => {
    button.addEventListener('click', function(e){
        row_number = button.value
        let delete_checkbox = document.querySelector(`.form-${row_number}.main [id*="DELETE"]`)
        if(delete_checkbox.checked){
            button.setAttribute('data-bs-target', `#modal-expiration-${row_number}`)
            delete_checkbox.checked = false
        } else {
            button.setAttribute('data-bs-target', '')
            delete_checkbox.checked = true
        }
        alterRowStatus(button)
    })
})

no_change_checkbox.forEach(checkbox => {
    checkbox.addEventListener('click', function(){
        alterRowStatus(checkbox)
    })
})


function toggleBandPricing(type_field){

    let form_num = type_field.name.match(/\d+/)[0]
    if (type_field.name.includes('band_1')){
        var field_type = 'band_1'
    } else {
        var field_type = 'band_2'
    }

    let band_fields = document.querySelectorAll(`[name*="-${form_num}-${field_type}_start"], [name*="-${form_num}-${field_type}_end"]`)
    if($(type_field).val() == ''){
        band_fields.forEach(field => {
            field.disabled = true
            field.value = ''
        })
    } else {
        band_fields.forEach(field => {
            field.disabled = false
        })
    }

}


function setAllDates(){
    let header_date_checkbox = document.querySelector('.header-date-open')
    let header_date_input = document.querySelectorAll('.header-date-setting .header-date-input')
    let date_fields = document.querySelectorAll('.form-row [name*="valid_from"]')

    if(header_date_checkbox.checked){
        date_fields.forEach(field => {
            field.value = header_date_input[0].value
            field.disabled = true
        })
    } else {
        header_date_input.forEach(input => {
            input.disabled = true
        })
    }

    header_date_checkbox.addEventListener('change', function() {
        if(this.checked){
            header_date_input.forEach(input => {
                input.disabled = false
            })
            date_fields.forEach(field => {
                field.disabled = true
                field.classList.remove('is-invalid')
            })
        } else {
            header_date_input.forEach(input => {
                input.disabled = true
                input.value = ""
            })
            i = 0
            date_fields.forEach(field => {
                let no_change_checkbox = document.querySelector(`.form-${i}.main [id*="no_change"]`)
                let delete_checkbox = document.querySelector(`.form-${i}.main [id*="DELETE"]`)
                if(!no_change_checkbox.checked && !delete_checkbox.checked){
                    field.disabled = false
                }
                i++

            })

        }
    });

    header_date_input.forEach(input => {
        input.addEventListener('keyup', function(){
            i = 0
            date_fields.forEach(field => {
                let no_change_checkbox = document.querySelector(`.form-${i}.main [id*="no_change"]`)
                let delete_checkbox = document.querySelector(`.form-${i}.main [id*="DELETE"]`)
                if(!no_change_checkbox.checked && !delete_checkbox.checked){
                    field.value = this.value
                }
                i++
            })
        })
    })

}

function alterRowStatus(button){
    let row_number

    button.classList.contains('hide-row') ? row_number = button.value : row_number = button.id.match(/\d+/)[0]
    let form_row = document.querySelectorAll(`.form-${row_number}.sub, .form-${row_number}.main`)
    let form_fields = document.querySelectorAll(`.form-${row_number} input, .form-${row_number} select`)
    let no_change_checkbox = document.querySelector(`.form-${row_number}.main [id*="no_change"]`)
    let delete_checkbox = document.querySelector(`.form-${row_number}.main [id*="DELETE"]`)

    if(delete_checkbox.checked || no_change_checkbox.checked){
        form_fields.forEach(field => {
            if(!field.classList.contains('no-change')) {
                field.disabled = true
                field.classList.remove('is-invalid')
            }
        })
        form_row.forEach(row => {
            row.classList.add('row-disabled')
        })
    } else {
        form_fields.forEach(field => {
            if(!field.name.includes('current_tax_rate')){
                field.disabled = false
            }
            let band_1_type = form_row[1].querySelector(`[name*="band_1_type"]`)
            toggleBandPricing(band_1_type)
            let band_2_type = form_row[1].querySelector(`[name*="band_2_type"]`)
            toggleBandPricing(band_2_type)
        })
        form_row.forEach(row => {
            row.classList.remove('row-disabled')
        })
    }

    if(button.classList.contains('hide-row')){
        if(delete_checkbox.checked){
            no_change_checkbox.checked = false
            no_change_checkbox.disabled = true
            button.classList.add('fa-recycle', 'text-success')
            button.classList.remove('fa-trash', 'text-danger')
        } else {
            no_change_checkbox.disabled = false
            button.classList.add('fa-trash', 'text-danger')
            button.classList.remove('fa-recycle', 'text-success')
        }
    } else {
        delete_checkbox.checked = false
        let old_pricing_fields = document.querySelectorAll(`.form-${row_number}.sub [name*="current_tax_rate"]`)
        let pricing_fields = document.querySelectorAll(`.form-${row_number}.sub [name$="pricing_amount"], .form-${row_number}.sub [name*="band_pricing"]`)
        if(no_change_checkbox.checked){
            i = 0
            pricing_fields.forEach(field => {
                field.value = old_pricing_fields[i].value
                i++
            })
        } else {
            pricing_fields.forEach(field => {
                field.value = ''
            })
        }
    }
}


let button_pressed_input = document.querySelector('.button-pressed-input')
let footer_buttons = document.querySelectorAll('.button-row button')

footer_buttons.forEach(button => {
    button.addEventListener('click', function(){
        button_pressed_input.value = this.value
        let form_fields = document.querySelectorAll('.form-row input, .form-row select')
        form_fields.forEach(field => {
            if(field.disabled){
                field.disabled = false
                }
            if(button_pressed_input.value != 'save'){
                if(field.required){
                    field.required = false
                }
            }
        })
    })
})

let create_new_button = document.querySelector('.create-new')
create_new_button?.addEventListener('click', function(){
    button_pressed_input.value = this.value
        let form_fields = document.querySelectorAll('.form-row input, .form-row select')
        form_fields.forEach(field => {
            if(field.disabled){
                field.disabled = false
                }
            if(button_pressed_input.value != 'Save'){
                if(field.required){
                    field.required = false
                }
            }
        })
})


function reInitializeHiddenRows(){
    form_row.forEach(row => {
        let delete_checkbox = row.querySelector('[id*="DELETE"]')
        let pricing_input = row.querySelector('[id*="pricing_amount"]')
        let no_change_checkbox = row.querySelector('[id*="no_change"]')
        let hide_row_icon = row.querySelector('.hide-row')
        let form_fields = row.querySelectorAll('.form-row input, .form-row select')

        if(delete_checkbox.checked){
            row.classList.add('row-disabled')
            hide_row_icon.classList.remove('fa-trash', 'text-danger')
            hide_row_icon.classList.add('fa-recycle', 'text-success')

            form_fields.forEach(field => {
                field.disabled = true
            })
        } else if (no_change_checkbox.checked){
            pricing_input.disabled = true
        }

    })
}

let add_band_buttons = document.querySelectorAll('.add-row')
let delete_band_buttons = document.querySelectorAll('.delete-row')

add_band_buttons.forEach(button => {
    button.addEventListener('click', alterBandInput)
})

delete_band_buttons.forEach(button => {
    button.addEventListener('click', function() {
        this.parentElement.parentElement.parentElement.remove()
    })
})


function alterBandInput(){
    let form_num = this.id.match(/\d+/)[0]
    let band_row = document.querySelectorAll(`.form-row.form-${form_num}`)
    let row_num = band_row.length

    let new_band_row = band_row[row_num-1].cloneNode(true)

    let current_pricing = new_band_row.querySelector(`[name*="-${form_num}-current_tax_rate"]`)
    let pricing_unit = new_band_row.querySelector('.pricing-unit')

    if(current_pricing != null){
        if(band_row.length == 3){
            current_pricing.parentElement.remove()
        } else {
            current_pricing.remove()
        }
    }

    if(pricing_unit != null){
        pricing_unit.remove()
    }

    let labels = new_band_row.querySelectorAll('label')
    labels.forEach(label => {
        label.remove()
    })

    let band_1_start = new_band_row.querySelector('[name*="band_1_start"]')
    let band_1_end = new_band_row.querySelector('[name*="band_1_end"]')
    let band_2_start = new_band_row.querySelector('[name*="band_2_start"]')
    let band_2_end = new_band_row.querySelector('[name*="band_2_end"]')

    if(band_1_end.value != ''){
        band_1_start.value = parseInt(band_1_end.value) + 1
        band_1_end.value = ''
    } else {
        band_1_start.value = ''
    }

    if(band_2_end.value != ''){
        band_2_start.value = parseInt(band_2_end.value) + 1
        band_2_end.value = ''
    } else {
        band_2_start.value = ''
    }


    if(band_row.length == 3){
        let new_div = document.createElement('div')
        new_div.classList.add('col', 'md-4', 'mb-3', 'deletion-col')
        let delete_band_button = document.createElement('button')
        delete_band_button.classList.add('fas', 'fa-minus', 'text-danger', 'delete-row')
        delete_band_button.type = 'button'
        delete_band_button.addEventListener('click', function() {
            this.parentElement.parentElement.parentElement.remove()
        })

        let add_button_div = new_band_row.querySelector('.add-col')

        new_div.append(delete_band_button)
        add_button_div.replaceWith(new_div)

    } else {
        let delete_band_button = new_band_row.querySelector('.delete-row')
        delete_band_button.addEventListener('click', function() {
            this.parentElement.parentElement.parentElement.remove()
        })
    }

    let insert_before = document.querySelector(`.form-${form_num}.insert-before-band`)
    this.parentElement.parentElement.parentElement.parentElement.insertBefore(new_band_row, insert_before)
    new_band_row.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));


    alterBandFieldNumbering(form_num)
}


function alterBandFieldNumbering(form_num){
    let band_1_start_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="band_1_start"]`)
    let band_1_end_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="band_1_end"]`)
    let band_2_start_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="band_2_start"]`)
    let band_2_end_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="band_2_end"]`)
    let band_pricing_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name$="pricing_amount"], .form-row.form-${form_num}.sub [name*="band_pricing_amount-additional"]`)

    if(band_1_start_fields.length > 1){
        let i = 0
        band_1_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_num}-band_1_start-additional-${form_num}-${i}`
                field.name = `${form_prefix}-${form_num}-band_1_start-additional-${form_num}-${i}`
            }

            i++
        })

        i = 0
        band_1_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_num}-band_1_end-additional-${form_num}-${i}`
                field.name = `${form_prefix}-${form_num}-band_1_end-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        band_2_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_num}-band_2_start-additional-${form_num}-${i}`
                field.name = `${form_prefix}-${form_num}-band_2_start-additional-${form_num}-${i}`
            }

            i++
        })

        i = 0
        band_2_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_num}-band_2_end-additional-${form_num}-${i}`
                field.name = `${form_prefix}-${form_num}-band_2_end-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        band_pricing_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-${form_num}-band_pricing_amount-additional-${form_num}-${i}`
                field.name = `${form_prefix}-${form_num}-band_pricing_amount-additional-${form_num}-${i}`
            }
            i++
        })
    }
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

application_method_fields = document.querySelectorAll('[name*="application_method"]')
fuel_application_method_fields = document.querySelectorAll('[name*="fuel_pricing_unit"]')


function showAppropriateChargeFields(charging_method, form_number){


    if(charging_method == 'Percentage of Net Price'){

        fuel_application_method_fields[form_number].disabled = true
        application_method_fields[form_number].disabled = true
        fuel_application_method_fields[form_number].parentElement.classList.remove('d-none')
        application_method_fields[form_number].parentElement.classList.add('d-none')
        $(fuel_application_method_fields[form_number]).val('').trigger('change')
        $(application_method_fields[form_number]).val('').trigger('change')
        // fuel_application_method_fields[form_number].removeAttribute('required')
        // application_method_fields[form_number].removeAttribute('required')

    } else if (charging_method == 'Fixed Cost'){

        fuel_application_method_fields[form_number].disabled = true
        application_method_fields[form_number].disabled = false
        fuel_application_method_fields[form_number].parentElement.classList.add('d-none')
        application_method_fields[form_number].parentElement.classList.remove('d-none')
        $(fuel_application_method_fields[form_number]).val('').trigger('change')
        // fuel_application_method_fields[form_number].removeAttribute('required')
        // application_method_fields[form_number].setAttribute('required', "")

    } else if (charging_method == 'Fixed Cost (Fuel Based)'){

        fuel_application_method_fields[form_number].disabled = false
        application_method_fields[form_number].disabled = true
        fuel_application_method_fields[form_number].parentElement.classList.remove('d-none')
        application_method_fields[form_number].parentElement.classList.add('d-none')
        $(application_method_fields[form_number]).val('').trigger('change')
        // fuel_application_method_fields[form_number].setAttribute('required', "")
        // application_method_fields[form_number].removeAttribute('required')

    }

}
