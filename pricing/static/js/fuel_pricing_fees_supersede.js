$(document).ready(() => {
    if(!$('#sidebarMenu').hasClass('contracted')){
        $('#sidebar-toggle').click()
    }
    setAllDates()

    // The destroy alone fixes the modal error on load
    setTimeout(() => {
        reInitializeSelect2()
    }, 500)
})

let quantity_band_type_fields = document.querySelectorAll(`[name*="quantity_band_uom"]`)
quantity_band_type_fields.forEach(field => {
    toggleBandPricing(field)
})

quantity_band_type_fields.forEach(field => {
    $(field).on('select2:select', function() {
        toggleBandPricing(field)
    })
    $(field).on('select2:clear', function(){
        toggleBandPricing(field)
    })
})

let weight_band_type_fields = document.querySelectorAll(`[name$="weight_band"]`)
weight_band_type_fields.forEach(field => {
    toggleBandPricing(field)
})

weight_band_type_fields.forEach(field => {
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
    let row_number = button.value
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
        let row_number = button.value
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
    if (type_field.name.includes('weight')){
        var field_type = 'weight'
    } else {
        var field_type = 'quantity'
    }

    let band_fields = document.querySelectorAll(`[name*="-${form_num}-${field_type}_band_start"], [name*="-${form_num}-${field_type}_band_end"]`)
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
    let date_fields = document.querySelectorAll('[name*="valid_from_date"]')

    if(header_date_checkbox.checked){
        date_fields.forEach(field => {
            field.value = header_date_input[0].value
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
            let i = 0
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
            let i = 0
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
            if(!field.name.includes('amount_old')){
                field.disabled = false
            }
            let quantity_band_type = form_row[0].querySelector(`[name*="quantity_band_uom"]`)
            toggleBandPricing(quantity_band_type)
            let weight_band_type = form_row[0].querySelector(`[name*="weight_band"]`)
            toggleBandPricing(weight_band_type)
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
        let old_pricing_fields = document.querySelectorAll(`.form-${row_number}.sub [name*="amount_old"]`)
        let pricing_fields = document.querySelectorAll(`.form-${row_number}.sub [name$="native_amount"], .form-${row_number}.sub [name*="band_pricing"]`)
        if(no_change_checkbox.checked){
            let i = 0
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


// function hideFormRow(){

//     row_number = this.id.match(/\d+/)[0]
//     let delete_checkbox = document.querySelector(`.row-${row_number}.main [id*="DELETE"]`)


//     initializeRows(this)

// }

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
            if(button_pressed_input.value != 'Save'){
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
        let pricing_input = row.querySelector('[id*="pricing_native_amount"]')
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
        this.closest('.form-row').remove()
    })
})


function alterBandInput(){
    let form_num = this.id.match(/\d+/)[0]
    let band_row = document.querySelectorAll(`.form-row.form-${form_num}`)
    let row_num = band_row.length

    let new_band_row = band_row[row_num-1].cloneNode(true)

    let current_pricing = new_band_row.querySelector(`[name*="-${form_num}-pricing_native_amount_old"]`)
    let pricing_unit = new_band_row.querySelector('.pricing-unit')

    if(current_pricing != null){
        if(band_row.length == 2){
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

    let quantity_band_start = new_band_row.querySelector('[name*="quantity_band_start"]')
    let quantity_band_end = new_band_row.querySelector('[name*="quantity_band_end"]')
    let weight_band_start = new_band_row.querySelector('[name*="weight_band_start"]')
    let weight_band_end = new_band_row.querySelector('[name*="weight_band_end"]')

    if(quantity_band_end.value != ''){
        quantity_band_start.value = parseInt(quantity_band_end.value) + 1
        quantity_band_end.value = ''
    } else {
        quantity_band_start.value = ''
    }

    if(weight_band_end.value != ''){
        weight_band_start.value = parseInt(weight_band_end.value) + 1
        weight_band_end.value = ''
    } else {
        weight_band_start.value = ''
    }


    if(band_row.length == 2){
        let new_div = document.createElement('div')
        new_div.classList.add('col', 'md-4', 'mb-3', 'deletion-col')
        let delete_band_button = document.createElement('button')
        delete_band_button.classList.add('fas', 'fa-minus', 'text-danger', 'delete-row')
        delete_band_button.type = 'button'
        delete_band_button.addEventListener('click', function() {
        this.closest('.form-row').remove()
        })

        let add_button_div = new_band_row.querySelector('.add-col')

        new_div.append(delete_band_button)
        add_button_div.replaceWith(new_div)

    } else {
        let delete_band_button = new_band_row.querySelector('.delete-row')
        delete_band_button.addEventListener('click', function() {
        this.closest('.form-row').remove()
        })
    }

    let insert_before = document.querySelector(`.form-${form_num}.insert-before-band`)
    this.parentElement.parentElement.parentElement.parentElement.insertBefore(new_band_row, insert_before)
    new_band_row.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));


    alterBandFieldNumbering(form_num)
}


function alterBandFieldNumbering(form_num){
    let quantity_band_start_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="quantity_band_start"]`)
    let quantity_band_end_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="quantity_band_end"]`)
    let weight_band_start_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="weight_band_start"]`)
    let weight_band_end_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name*="weight_band_end"]`)
    let band_pricing_fields = document.querySelectorAll(`.form-row.form-${form_num}.sub [name$="pricing_native_amount"], .form-row.form-${form_num}.sub [name*="pricing_native_amount-additional"]`)

    if(quantity_band_start_fields.length > 1){
        let i = 0
        quantity_band_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_existing-fuel-fee-rate-${form_num}-quantity_band_start-additional-${form_num}-${i}`
                field.name = `existing-fuel-fee-rate-${form_num}-quantity_band_start-additional-${form_num}-${i}`
            }

            i++
        })

        i = 0
        quantity_band_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_existing-fuel-fee-rate-${form_num}-quantity_band_end-additional-${form_num}-${i}`
                field.name = `existing-fuel-fee-rate-${form_num}-quantity_band_end-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        weight_band_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_existing-fuel-fee-rate-${form_num}-weight_band_start-additional-${form_num}-${i}`
                field.name = `existing-fuel-fee-rate-${form_num}-weight_band_start-additional-${form_num}-${i}`
            }

            i++
        })

        i = 0
        weight_band_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_existing-fuel-fee-rate-${form_num}-weight_band_end-additional-${form_num}-${i}`
                field.name = `existing-fuel-fee-rate-${form_num}-weight_band_end-additional-${form_num}-${i}`
            }
            i++
        })

        i = 0
        band_pricing_fields.forEach(field => {
            if(i > 0){
                field.id = `id_existing-fuel-fee-rate-${form_num}-band_pricing_native_amount-additional-${form_num}-${i}`
                field.name = `existing-fuel-fee-rate-${form_num}-band_pricing_native_amount-additional-${form_num}-${i}`
            }
            i++
        })
    }
}


document.querySelectorAll('[id$="-specific_handler"]').forEach((el) => {
  $(el).on('change', updateSpecificHandlerCheckbox);
  $(el).trigger('change');
});


function updateSpecificHandlerCheckbox() {
  let specificHandlerField = this
  let specificHandlerCheckbox = this.parentElement.parentElement.parentElement
    .querySelector('[id*="-specific_handler_is_excluded"]');

  if (!$(specificHandlerField).val()) {
    specificHandlerCheckbox.checked = false;
    specificHandlerCheckbox.disabled = true;
    $(specificHandlerCheckbox.parentElement).addClass('disabled');
  } else {
    specificHandlerCheckbox.disabled = false;
    $(specificHandlerCheckbox.parentElement).removeClass('disabled');
  }
}


function reInitializeSelect2() {
  $('.django-select2').each(function () {
    $(this).djangoSelect2("destroy")
    $(this).djangoSelect2({
      dropdownParent: $(this).parent(),
      width: '100%',
    });
  });
}


import './includes/_fee_validity_periods.js';
import './includes/_supplier_exchange_rate.js';
