$(document).ready(() => {
    if(!$('#sidebarMenu').hasClass('contracted')){
        $('#sidebar-toggle').click()
    }
    setAllDates()
    reInitializeHiddenRows()
    initializeTooltipOnOverflow()

    // The destroy alone fixes the modal error on load
    setTimeout(() => {
        reInitializeSelect2()
    }, 500)

    let tooltipText = document.querySelectorAll('.tooltiptext');

    tooltipText.forEach(tooltip => {
        if (tooltip.scrollHeight <= 280) {
            tooltip.style.maxHeight = tooltip.scrollHeight + 'px';
            tooltip.style.overflowY = 'hidden';
        }
    })
})

function reInitializeSelect2(){
    $('.django-select2').each(function () {
            $(this).djangoSelect2("destroy")
            $(this).djangoSelect2({
                dropdownParent: $(this).parent(),
                width: '100%'
            });
    });
}

function setAllDates(){
    let header_date_checkbox = $('.header-date-open')
    let header_date_input = $('.header-date-setting .header-date-input')
    let table_date_fields = $('.table-form-body .table-date-input')

    let new_header_date_checkbox = $('.new-header-date-open')
    let new_header_date_input = $('.new-header-date-setting .header-date-input')
    let new_table_date_fields = $('.table-new-form-body .table-date-input')
    let new_table_date_fields_valid_from = $('.table-new-form-body .valid-from')
    let new_table_date_fields_valid_to = $('.table-new-form-body .valid-to')
    
    if(header_date_checkbox.is(':checked')){
        header_date_input.prop("disabled", false)
        table_date_fields.prop("readonly", true)
    } else {
        header_date_input.prop("disabled", true)
    }

    header_date_checkbox.change(function() {
        if(this.checked){
            header_date_input.prop("disabled", false)
            table_date_fields.prop("readonly", true)
        } else {
            header_date_input.prop("disabled", true)
            header_date_input.val("")
            table_date_fields.prop("readonly", false)

        }
    });

    if(new_header_date_checkbox.is(':checked')){
        new_header_date_input.prop("disabled", false)
        new_table_date_fields.prop("readonly", true)
        new_table_date_fields_valid_from.val($('#id_new-date-valid_from').val())
        new_table_date_fields_valid_to.val($('#id_new-date-valid_to').val())
    } else {
        new_header_date_input.prop("disabled", true)
        new_table_date_fields.prop("readonly", false)
    }

    new_header_date_checkbox.change(function() {
        if(this.checked){
            new_header_date_input.prop("disabled", false)
            new_table_date_fields.prop("readonly", true)
        } else {
            new_header_date_input.prop("disabled", true)
            new_header_date_input.val("")
            new_table_date_fields.prop("readonly", false)
            new_table_date_fields.val("")

        }
    });

    new_header_date_input.on('keyup', function(){
        if($(this).is('#id_new-date-valid_from')){
            new_table_date_fields_valid_from.val($(this).val())
        } else if($(this).is('#id_new-date-valid_to')){
            new_table_date_fields_valid_to.val($(this).val())
        }
    })

    
}

let form_container = document.querySelector('.table-new-form-body')

let total_new_forms = document.querySelector('#id_new-pricing-TOTAL_FORMS')
let current_new_forms = document.querySelectorAll('.new-form-row:not(.d-none)')

total_new_forms.setAttribute('value', current_new_forms.length)
let add_row_buttons = document.querySelectorAll('.add-row, .add-5-rows')
let hide_row_buttons = document.querySelectorAll('.hide-row, .new-hide-row')

let form_fields = document.querySelectorAll('.form-row input, .form-row select, .form-modal input, .form-modal select, .form-modal textarea')

add_row_buttons.forEach(button => {
    button.addEventListener('click', addFormRow)
})

hide_row_buttons.forEach(button => {
    button.addEventListener('click', hideFormRow)
})

function addFormRow(e){
    e.preventDefault()
    let max = 5
    if(e.target.classList.contains('add-row')){
        max = 1
    }
    let i = 0;
    let new_form_row = document.querySelectorAll('.new-form-row')
    let new_form_modal = document.querySelectorAll('.new-form-modal')
    let form_regex = RegExp(`new-pricing-[0-9]{1,2}-`,'g') // Regex to find all instances of the form and modal number
    let modal_regex = RegExp(`new-modal-[0-9]{1,2}`,'g')

    if(new_form_row[new_form_row.length-1].classList.contains('d-none')){
        new_form_row[new_form_row.length-1].classList.remove('d-none')
        new_form_modal[new_form_modal.length-1].classList.remove('d-none')
        total_new_forms.setAttribute('value', `${parseInt(total_new_forms.value)+1}`)
        i = 1;
    }

    for(i; i < max; i++){
        new_form_row = document.querySelectorAll('.new-form-row')
        new_form_modal = document.querySelectorAll('.new-form-modal')

        let form_num = new_form_row.length-1
        let modal_num = new_form_modal.length-1

        let new_row = new_form_row[form_num].cloneNode(true)
        let new_modal = new_form_modal[modal_num].cloneNode(true)

        form_num++
        modal_num++
        let check_form = document.querySelector(`[name='new-pricing-${form_num}-id']`)
        while (check_form != undefined){
            form_num++
            modal_num++
            check_form = document.querySelector(`[name='new-pricing-${form_num}-id']`)
        }

        new_row.innerHTML = new_row.innerHTML.replace(form_regex, `new-pricing-${form_num}-`)
        // new_row.innerHTML = new_row.innerHTML.replace('is-invalid', '')
        new_row.innerHTML = new_row.innerHTML.replace(modal_regex, `new-modal-${form_num+1}`)
        new_row.classList.remove('d-none')
        delete_button = new_row.querySelector('.new-hide-row')
        delete_button.value = new_form_row.length+1
        delete_button.addEventListener('click', hideFormRow)
        
        new_modal.innerHTML = new_modal.innerHTML.replace(form_regex, `new-pricing-${modal_num}-`)
        new_modal.innerHTML = new_modal.innerHTML.replace(modal_regex, `new-modal-${modal_num+1}`)
        // Since we are copying already initialized select2, when we reinitiailize, we have to hide the old one
        current_select2 = new_modal.querySelectorAll('.select2, .select2-container')
        current_select2.forEach(function(field){
              field.classList.add('d-none')
        })

        form_container.insertBefore(new_row, new_form_row[form_num])
        form_container.append(new_modal)

        total_new_forms.setAttribute('value', `${parseInt(total_new_forms.value)+1}`) //Increment the number of total forms in the management form
    }
    setAllDates()
    reInitializeSelect2()
    initializeTooltipOnOverflow()
    }

function resetRowNumbers(){
    let delete_buttons = document.querySelectorAll('.new-hide-row')
    new_value = 1
    delete_buttons.forEach(button => {
        button.value = new_value
        new_value++
    })
}

let form_row = document.querySelectorAll('.form-row')
let form_modal = document.querySelectorAll('.form-modal')

function hideFormRow(e){
    e.preventDefault()

    if(e.target.classList.contains('hide-row')){

        let form_fields = form_row[this.value-1].querySelectorAll('input, select')
        let modal_fields = form_modal[this.value-1].querySelectorAll('input, select, textarea')
        let delete_checkbox = form_row[this.value-1].querySelector('[id*="DELETE"]')
        let pricing_input = form_row[this.value-1].querySelector('[id*="pricing_native_amount"]')
       
        if(pricing_input.classList.contains('is-invalid')){
            pricing_input.classList.remove('is-invalid')
        }

        if(delete_checkbox.checked){
            delete_checkbox.checked = false
        } else {
            delete_checkbox.checked = true
        }

        // Note: readOnly is not working for <select>
        form_fields.forEach(field => {
            if(field.disabled){
                field.disabled = false
            } else {
                field.disabled = true
            }
        })

        modal_fields.forEach(field => {
            if(field.disabled){
                field.disabled = false
            } else {
                field.disabled = true
            }
        })

        if(form_row[this.value-1].classList.contains('row-disabled')){
            form_row[this.value-1].classList.remove('row-disabled')
            this.classList.remove('fa-recycle', 'text-success')
            this.classList.add('fa-trash', 'text-danger')
        } else {
            form_row[this.value-1].classList.add('row-disabled')
            this.classList.remove('fa-trash', 'text-danger')
            this.classList.add('fa-recycle', 'text-success')
        }

    } else {
        let new_form_row = document.querySelectorAll('.new-form-row')
        let new_form_modal = document.querySelectorAll('.new-form-modal')

        if(total_new_forms.value == 1){
            new_form_row[0].classList.add('d-none')
            new_form_modal[0].classList.add('d-none')
        } else {
            new_form_row[this.value-1].remove()
            new_form_modal[this.value-1].remove()
            setAllDates()
            resetRowNumbers()
        }
        total_new_forms.setAttribute('value', `${total_new_forms.value-1}`)
    }
}

let button_pressed_input = document.querySelector('.button-pressed-input')
let footer_buttons = document.querySelectorAll('.button-row button')
let refresh_button = document.querySelector('.refresh')

footer_buttons.forEach(button => {
    refresh_button, button.addEventListener('click', function(){
        button_pressed_input.value = this.value
        form_fields.forEach(field => {
        if(field.disabled){
            field.disabled = false
        }
        if($('#sidebarMenu').hasClass('contracted')){
            $('#sidebar-toggle').click()
        }
        })
    })
})

function reInitializeHiddenRows(){
    form_row.forEach(row => {
        let delete_checkbox = row.querySelector('[id*="DELETE"]')
        let hide_row_icon = row.querySelector('.hide-row')

        if(delete_checkbox.checked){
            row.classList.add('row-disabled')
            hide_row_icon.classList.remove('fa-trash', 'text-danger')
            hide_row_icon.classList.add('fa-recycle', 'text-success')

            let row_fields = row.querySelectorAll('input, select')
            row_fields.forEach(field => {
                    field.disabled = true
            })
        }
    })
}

function isOverflown(field, selection) {
    let dummy = document.createElement('div')
    dummy.innerText = selection.innerText
    dummy.style.position = 'absolute'
    dummy.style.visibility = 'hidden'
    dummy.style.fontSize = '0.75rem'
    dummy.style.padding = '0.5rem 1rem'
    document.body.insertBefore(dummy, document.body.firstChild);
    const measuredWidth = dummy.offsetWidth;
    document.body.removeChild(dummy);
    if (measuredWidth >= field.offsetWidth){
        return true
    } else {
        return false
    }

  }

function initializeTooltipOnOverflow(){
    let table_fields = document.querySelectorAll('.overflows')
    table_fields.forEach(field => {
        let selection = field.options[field.selectedIndex]
        if(!field.parentNode.parentNode.classList.contains('d-none') && isOverflown(field, selection)){
            field.setAttribute('data-bs-toggle', 'tooltip')
            field.setAttribute('data-bs-placement', 'top')
            field.setAttribute('data-bs-original-title', selection.innerText)
            }

        field.addEventListener('click', () => {
            eventListenerForOverflow(field)
        })

        field.parentNode.parentNode.addEventListener('mouseenter', () => {
            eventListenerForOverflow(field)
        })

    })
    initializeTooltips()
}

function eventListenerForOverflow(field){
    let selection = field.options[field.selectedIndex]
    if(!field.hasAttribute('data-bs-toggle')){
        field.setAttribute('data-bs-toggle', 'tooltip')
        field.setAttribute('data-bs-placement', 'top')
    }
    if(isOverflown(field, selection)){
        field.setAttribute('data-bs-original-title', selection.innerText)
        initializeTooltips()
    } else {
        field.setAttribute('data-bs-original-title', '')
    }

    let tooltip = document.querySelector('.tooltip')
    if(tooltip != null){
        tooltip.remove()
    }
}

function initializeTooltips(){
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
}

