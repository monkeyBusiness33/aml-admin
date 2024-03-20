onInit()

function onInit(){
    form_prefix = "tax-rule"
    alterBandFieldNumbering()

    let tax_form_hidden_divs = document.querySelectorAll('.tax-form .d-none')
    let tax_form_hidden_fields = document.querySelectorAll('.tax-form select:not(#id_tax_instance), .tax-form input')

    let create_tax_button = document.querySelector('.new-tax-button')
    let region_field = document.querySelector('#id_applicable_region')
    let category_field = document.querySelector("#id_category")
    let local_name_field = document.querySelector('#id_local_name')
    let short_name_field = document.querySelector('#id_short_name')
    let tax_field = document.querySelector('#id_tax_instance')

    current_form = document.querySelector('.form-title')

    if(create_tax_button != null){
        create_tax_button.addEventListener('click', () => {
            alterHiddenFields(tax_form_hidden_divs)
            $(tax_field).val('').trigger('change')
            toggleRequiredAttributes(tax_field)
        })
        if(region_field != null){
            region_field.disabled = true
        }
        let tax_label = document.querySelector("label[for=id_tax_instance]")
        tax_label.classList.add('required')
        tax_field.required = true

        if(category_field.value != '' || local_name_field.value != ''){
            create_tax_button.click()
        } else if ($(tax_field).val() != ''){
            $(category_field).val('').trigger('change')
            $(local_name_field).val('').trigger('change')
            $(short_name_field).val('').trigger('change')
        }

    } else {
        toggleRequiredAttributes(category_field)
    }

    let vat_applicable_checkbox = document.querySelector('#id_tax-rule-0-taxed_by_vat')
    taxable_tax_section = document.querySelector('.taxable-taxes')

    if(taxable_tax_section != null){
        togglePrimaryTaxes(vat_applicable_checkbox)
        vat_applicable_checkbox.addEventListener('click', () => {
            togglePrimaryTaxes(vat_applicable_checkbox)
        })
    }


    let category_label = document.querySelector("label[for=id_category]")
    category_label.classList.add('required')

    let specific_fuel_field = document.querySelector('#id_tax-rule-0-specific_fuel')
    let specific_fuel_cat_field = document.querySelector('#id_tax-rule-0-specific_fuel_cat')
    let specific_fee_category_field = document.querySelector('#id_tax-rule-0-specific_fee_category')

    specific_fuel_field.disabled = true
    specific_fuel_cat_field.disabled = true
    specific_fee_category_field.disabled = true

    $(specific_fuel_field).on('select2:select', () => {
        $(specific_fuel_cat_field).val('').trigger('change')
        specific_fuel_cat_field.disabled = true
    })

    $(specific_fuel_field).on('select2:clear', () => {
        specific_fuel_cat_field.disabled = false
    })

    $(specific_fuel_cat_field).on('select2:select', () => {
        $(specific_fuel_field).val('').trigger('change')
        specific_fuel_field.disabled = true
    })

    $(specific_fuel_cat_field).on('select2:clear', () => {
        specific_fuel_field.disabled = false
    })

    add_band_button = document.querySelector('.new-band-button')
    revert_button = document.querySelector('.revert-button')

    if(add_band_button != null){
        add_band_button.addEventListener('click', addBandRow)
        revert_button.addEventListener('click', revertToDefault)
    }

    let applies_to_fuel_checkbox = document.querySelector('#id_tax-rule-0-applies_to_fuel')
    let applies_to_fees_checkbox = document.querySelector('#id_tax-rule-0-applies_to_fees')

    if ($(specific_fuel_cat_field).val() === '') {
        enableOnCheckboxCheck(applies_to_fuel_checkbox, specific_fuel_field)
    }

    if ($(specific_fuel_field).val() === '') {
        enableOnCheckboxCheck(applies_to_fuel_checkbox, specific_fuel_cat_field)
    }

    enableOnCheckboxCheck(applies_to_fees_checkbox, specific_fee_category_field)

    applies_to_fuel_checkbox.addEventListener('change', () => {
        enableOnCheckboxCheck(applies_to_fuel_checkbox, specific_fuel_field)
        enableOnCheckboxCheck(applies_to_fuel_checkbox, specific_fuel_cat_field)
        $(specific_fuel_field).val('').trigger('change')
        $(specific_fuel_cat_field).val('').trigger('change')
    })

    applies_to_fees_checkbox.addEventListener('change', () => {
        enableOnCheckboxCheck(applies_to_fees_checkbox, specific_fee_category_field)
        $(specific_fee_category_field).val('').trigger('change')
    })

    applies_to_fuel_checkbox.addEventListener('click', () => {
        if(!applies_to_fuel_checkbox.checked && !applies_to_fees_checkbox.checked){
            applies_to_fees_checkbox.checked = true
            enableOnCheckboxCheck(applies_to_fees_checkbox, specific_fee_category_field)
        }
    })
    applies_to_fees_checkbox.addEventListener('click', () => {
        if(!applies_to_fuel_checkbox.checked && !applies_to_fees_checkbox.checked){
            applies_to_fuel_checkbox.checked = true
            enableOnCheckboxCheck(applies_to_fuel_checkbox, specific_fuel_field)
            enableOnCheckboxCheck(applies_to_fuel_checkbox, specific_fuel_cat_field)
        }
    })

    let valid_ufn_checkbox = document.querySelector('#id_tax-rule-0-valid_ufn')
    let valid_to_field = document.querySelector('#id_tax-rule-0-valid_to')

    clearOnCheckboxCheck(valid_ufn_checkbox, valid_to_field)
    updateCheckboxExclusiveWithField(valid_ufn_checkbox, valid_to_field)

    valid_ufn_checkbox.addEventListener('change', () => {
        clearOnCheckboxCheck(valid_ufn_checkbox, valid_to_field)
    })

    valid_to_field.addEventListener('input', () => {
        updateCheckboxExclusiveWithField(valid_ufn_checkbox, valid_to_field)
    })

    let delete_band_buttons = document.querySelectorAll('.delete-row')
    if(delete_band_buttons != null){
        delete_band_buttons.forEach(button => {
            button.addEventListener('click', function() {
                this.parentElement.parentElement.remove()
                alterBandFieldNumbering()
            })
        })
    }

    let private_checkbox = document.querySelector('[name*="applies_to_private"]')
    let commercial_checkbox = document.querySelector('[name*="applies_to_commercial"]')

    private_checkbox.addEventListener('click', () => {
        if(!private_checkbox.checked && !commercial_checkbox.checked){
            commercial_checkbox.checked = true
        }
    })
    commercial_checkbox.addEventListener('click', () => {
        if(!private_checkbox.checked && !commercial_checkbox.checked){
            private_checkbox.checked = true
        }
    })

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

function reInitializePrimaryVATField(){
    $('.django-select2').each(function () {
        if($(this).attr('name') == 'tax-rule-0-taxable_tax'){
            $(this).select2("destroy")
            $(this).djangoSelect2({
                dropdownParent: $(this).parent(),
                width: '100%',
                templateResult: formatSearch,
                templateSelection: formatSelected,
            });
        }
    });
}


$(document).ready(function(){

    setTimeout(() => {
        reInitializePrimaryVATField()
    }, 300)

    let notification_modal = document.getElementById('notificationModal')
    if (notification_modal){
        $(notification_modal).modal('show')
    }

    if(add_band_button != null){
        let charging_method_field = $('[name*="tax_rule_charging_method"]')
        showAppropriateChargeFields(charging_method_field.select2('data')[0].text)

        charging_method_field.on('select2:select', function () {
            var method_selection = charging_method_field.select2('data')[0].text
            showAppropriateChargeFields(method_selection)
        })

        let percentage_method = $('[name*="tax_percentage_rate_application_method"]')
        percentage_method.on('select2:select', function () {
            if(getFormChargingMethod == 'band-based'){
                alterPricingFields(percentage_method.select2('data')[0].text)
            }
        })


        band_1_type_field = $(`[name*="band_1_type"]`)
        band_2_type_field = $(`[name*="band_2_type"]`)
        let band_1_bands = document.querySelectorAll('.band-1 input')
        let band_2_bands = document.querySelectorAll('.band-2 input')

        let initial_band_1_selection = band_1_type_field.select2('data')[0].text
        let initial_band_2_selection = band_2_type_field.select2('data')[0].text
        setConditionalRequiredAttributes(band_1_bands, initial_band_1_selection)
        setConditionalRequiredAttributes(band_2_bands, initial_band_2_selection)

        if(band_1_type_field.select2('data')[0].text != "" || band_2_type_field.select2('data')[0].text != ""){
            showAppropriateChargeFields(getCurrentChargingMethod(), getFormChargingMethod())
            changeAmountField('band-based')

        }

        band_1_type_field.on('select2:select', function() {
            switchBetweenPricingType($(this))
            let band_1_bands = document.querySelectorAll('.band-1 input')
            setConditionalRequiredAttributes(band_1_bands, band_1_type_field.select2('data')[0].text)

        })

        band_1_type_field.on('select2:clear', function() {
            let band_1_bands = document.querySelectorAll('.band-1 input')
            setConditionalRequiredAttributes(band_1_bands, band_1_type_field.select2('data')[0].text)
            band_1_bands.forEach(band => {
                band.value = ''
            })
        })

        band_2_type_field.on('select2:select', function() {
            switchBetweenPricingType($(this))
            let band_2_bands = document.querySelectorAll('.band-2 input')
            setConditionalRequiredAttributes(band_2_bands, band_2_type_field.select2('data')[0].text)
        })

        band_2_type_field.on('select2:clear', function() {
            let band_2_bands = document.querySelectorAll('.band-2 input')
            setConditionalRequiredAttributes(band_2_bands, band_2_type_field.select2('data')[0].text)
            band_2_bands.forEach(band => {
                band.value = ''
            })
        })

    } else {
        showAppropriateChargeFields('Percentage of Net Price', 'default')
    }

})

function togglePrimaryTaxes(checkbox){
    let label = document.querySelector('[for="id_tax-rule-0-taxable_tax"]')
    let field = document.querySelector('[name*="taxable_tax"]')

    if(checkbox.checked){
        taxable_tax_section.classList.remove('d-none')
        label.classList.add('required')
        field.required = true
    } else {
        taxable_tax_section.classList.add('d-none')
        label.classList.remove('required')
        field.required = false
        $(field).val('').trigger('change')
    }
}


function getFormChargingMethod(){

    let band_rows = document.querySelectorAll('.band-row')
    let first_row_fields = document.querySelectorAll('.band-row input')

    first_row_has_data = false
    first_row_fields.forEach(field => {
        if(field.value != ""){
            first_row_has_data = true
        }
    })

    if ((getBandOneType() != '' || getBandTwoType() != '' || band_rows.length > 1 || first_row_has_data)){
        return 'band-based'
    } else {
        return 'default'
    }
}

function alterPricingFields(selection){
    let band_pricing_fields = document.querySelectorAll('.band-pricing')

        band_pricing_fields.forEach(field => {
            field.classList.remove('d-none')
        })
        showAppropriateChargeFields('Percentage of Net Price')


}

function switchBetweenPricingType(band_field){

    selected_data = band_field.select2('data')[0].text
    let band_rows = document.querySelectorAll(`.band-row`)

    if(selected_data != "" && selected_data != "---------" ){
        changeAmountField('band-based')

    } else if (selected_data == "" && band_rows.length == 1) {
        changeAmountField('default')
    }
}


function changeAmountField(charging_method){
    let band_pricing_field = document.querySelector(`#id_tax-rule-0-band_pricing_amount`)
    let band_pricing_field_label = document.querySelector('[for*=band_pricing_amount]')
    let method_field = document.querySelector(`#id_tax-rule-0-band_method`)
    let method_field_label = document.querySelector('[for*="band_method"]')
    let default_pricing_fields = document.querySelectorAll('.default-pricing input')


    if(charging_method == 'band-based'){
        band_pricing_field.required = true
        band_pricing_field_label.classList.add('required')
        band_pricing_field.parentElement.parentElement.classList.remove('d-none')

        if(getCurrentChargingMethod() == 'Percentage of Net Price'){
            method_field.required = true
            method_field_label.classList.add('required')
            method_field.parentElement.parentElement.classList.remove('d-none')
        } else {
            method_field.required = false
            method_field_label.classList.remove('required')
            method_field.parentElement.parentElement.classList.add('d-none')
        }

        default_pricing_fields.forEach(field => {
            field.required = false
            field.parentElement.parentElement.classList.add('d-none')
        })
        alterBandPricingLabel()

    } else if (charging_method == 'default') {
        band_pricing_field.required = false
        band_pricing_field_label.classList.remove('required')
        band_pricing_field.parentElement.parentElement.classList.add('d-none')
    }

}


function addBandRow(){
    changeAmountField('band-based')
    let band_row = document.querySelectorAll(`.band-row`)
    let row_num = band_row.length

    let new_band_row = band_row[row_num-1].cloneNode(true)

    let labels = new_band_row.querySelectorAll('label')
    labels.forEach(label => {
        label.remove()
    })

    let bands = new_band_row.querySelectorAll('input')
    bands.forEach(band => {
        band.value = ""
    })

    let method_field = new_band_row.querySelector('select')
    let method_span = new_band_row.querySelector('span')
    method_span.remove()
    $(method_field).val('').trigger('change')

    let pricing_field = new_band_row.querySelector('[name*="pricing_amount"]')
    pricing_field.required = true

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

    let insert_before = document.querySelector(`.insert-before-band`)
    this.parentElement.insertBefore(new_band_row, insert_before)
    new_band_row.querySelectorAll('.auto-round-to-step').forEach(el => el.addEventListener('change', roundToStep));

    showAppropriateChargeFields()

    alterBandPricingLabel()
    alterBandFieldNumbering()

}

function alterBandPricingLabel(){
    let band_label = document.querySelector('label[for=id_tax-rule-0-band_pricing_amount]')
    if(getCurrentChargingMethod() == 'Percentage of Net Price'){
        band_label.innerHTML = 'Percentage'
    } else {
        band_label.innerHTML = 'Tax Unit Rate'
    }
}

function showAppropriateChargeFields(selection = getCurrentChargingMethod(), charging_method = getFormChargingMethod()){

    let fixed_rate_method_div = document.querySelector('.fixed-rate')
    let percent_rate_method_div  = document.querySelector('.percent-rate')
    let fixed_fuel_rate_method_div  = document.querySelector('.fixed-rate-fuel')

    let fixed_amount_div = document.querySelector('.fixed-rate-amount')
    let percentage_amount_div = document.querySelector('.percentage-rate-amount')

    let percentage_method_field = document.querySelector('[name*="tax_percentage_rate_application_method"]')
    let fixed_rate_method_field = document.querySelector('[name*="tax_unit_rate_application_method"]')
    let fixed_fuel_rate_method_field = document.querySelector('[name*="fuel_pricing_unit"]')

    let percentage_amount_field = document.querySelector('[name$="tax_percentage_rate"]')
    let fixed_amount_field = document.querySelector('[name$="tax_unit_rate"]')

    let band_pricing_divs = document.querySelectorAll('.band-pricing')
    let band_pricing_fields = document.querySelectorAll('.band-pricing input')

    let band_method_divs = document.querySelectorAll('.band-method')
    let band_method_fields = document.querySelectorAll('[name*="band_method"]')

    if(selection == 'Fixed Cost'){
        fixed_rate_method_div.classList.remove('d-none')
        percent_rate_method_div.classList.add('d-none')
        fixed_fuel_rate_method_div.classList.add('d-none')

        $(percentage_method_field).val('').trigger('change')
        $(fixed_fuel_rate_method_field).val('').trigger('change')
        percentage_amount_field.value = ''


        if(charging_method == 'default'){
            fixed_amount_div.classList.remove('d-none')
            percentage_amount_div.classList.add('d-none')

        } else {
            band_method_divs.forEach(div => {
                div.classList.add('d-none')
            })
            band_method_fields.forEach(field => {
                field.required = false
                $(field).val('').trigger('change')
            })
        }

    } else if (selection == 'Fixed Cost (Fuel Based)'){
        fixed_rate_method_div.classList.add('d-none')
        percent_rate_method_div.classList.add('d-none')
        fixed_fuel_rate_method_div.classList.remove('d-none')

        $(percentage_method_field).val('').trigger('change')
        $(fixed_rate_method_field).val('').trigger('change')
        percentage_amount_field.value = ''

        if(charging_method == 'default'){
            fixed_amount_div.classList.remove('d-none')
            percentage_amount_div.classList.add('d-none')

        } else {
            band_method_divs.forEach(div => {
                div.classList.add('d-none')
            })
            band_method_fields.forEach(field => {
                field.required = false
                $(field).val('').trigger('change')
            })
        }

    } else if (selection == 'Percentage of Net Price'){
        fixed_rate_method_div.classList.add('d-none')
        percent_rate_method_div.classList.remove('d-none')
        fixed_fuel_rate_method_div.classList.add('d-none')

        $(fixed_fuel_rate_method_field).val('').trigger('change')
        $(fixed_rate_method_field).val('').trigger('change')
        fixed_amount_field.value = ''

        band_method_fields[0].previousElementSibling.classList.add('required')


        if(charging_method == 'default'){
            fixed_amount_div.classList.add('d-none')
            percentage_amount_div.classList.remove('d-none')

            band_method_divs.forEach(div => {
                div.classList.add('d-none')
            })
            band_method_fields.forEach(field => {
                field.required = false
                $(field).val('').trigger('change')
            })

        } else {
            band_method_divs.forEach(div => {
                div.classList.remove('d-none')
            })
            band_method_fields.forEach(field => {
                field.required = true
            })

            percentage_method_field.required = false
            percentage_method_field.parentElement.parentElement.classList.add('d-none')
        }
    }

    if(charging_method == 'default'){

        band_pricing_fields.forEach(field => {
            field.value = ""
            field.classList.remove('is-invalid')
            field.removeAttribute('required')
            if(field.nextElementSibling && field.nextElementSibling.classList.contains('invalid-feedback')){
                field.nextElementSibling.remove()
            }
        })

        band_method_fields.forEach(field => {
            field.required = false
            $(field).val('').trigger('change')
            field.parentElement.parentElement.classList.add('d-none')
        })
    }

    if(charging_method == 'band-based'){
        fixed_amount_div.classList.add('d-none')
        percentage_amount_div.classList.add('d-none')

        band_pricing_divs.forEach(div => {
            div.classList.remove('d-none')
        })
        band_pricing_fields.forEach(field => {
            if(field.nextElementSibling && field.nextElementSibling.classList.contains('invalid-feedback')){
                field.nextElementSibling.remove()
            }
            field.required = true
        })
    alterBandPricingLabel()

    }
    let all_fields = document.querySelectorAll('.charging-methods select, .charging-methods input')

    alterFieldDisabledAttr(all_fields)
    toggleRequiredAttributes(all_fields)

}


function removeBandFields(){
    let band_rows = document.querySelectorAll(`.band-row`)
    let band_pricing_field = document.querySelector(`#id_tax-rule-0-band_pricing_amount`)

    let i = 0
    band_rows.forEach(row => {
        if(i > 0){
            row.remove()
        }
        i++
    })

    band_pricing_field.required = false
    band_pricing_field.parentElement.parentElement.classList.add('d-none')

}

function revertToDefault(){

    removeBandFields()

    let band_fields = document.querySelectorAll(`.band-row input`)

    band_1_type_field.val('').trigger('change')
    band_2_type_field.val('').trigger('change')

    band_fields.forEach(field => {
        field.classList.remove('is-invalid')
        field.value = ""
        if(field.previousElementSibling != null){
            field.previousElementSibling.classList.remove('required')
        }
        field.required = false
    })
    showAppropriateChargeFields(getCurrentChargingMethod())

}


function alterBandFieldNumbering(){
    let band_1_start_fields = document.querySelectorAll('.band-1-start input')
    let band_1_end_fields = document.querySelectorAll('.band-1-end input')
    let band_2_start_fields = document.querySelectorAll('.band-2-start input')
    let band_2_end_fields = document.querySelectorAll('.band-2-end input')
    let taxed_by_primary_vat_fields = document.querySelectorAll('.taxable-tax input')
    let band_method_fields = document.querySelectorAll('.band-method select')

    let band_pricing_fields = document.querySelectorAll('.band-pricing input')

    if(band_1_start_fields.length > 1){
        let i = 0
        band_1_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-0-band_1_start-additional-0-${i}`
                field.name = `${form_prefix}-0-band_1_start-additional-0-${i}`
            }
            i++
        })

        i = 0
        band_1_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-0-band_1_end-additional-0-${i}`
                field.name = `${form_prefix}-0-band_1_end-additional-0-${i}`
            }
            i++
        })
        i = 0
        band_2_start_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-0-band_2_start-additional-0-${i}`
                field.name = `${form_prefix}-0-band_2_start-additional-0-${i}`
            }
            i++
        })

        i = 0
        band_2_end_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-0-band_2_end-additional-0-${i}`
                field.name = `${form_prefix}-0-band_2_end-additional-0-${i}`
            }
            i++
        })

        i = 0
        band_pricing_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-0-band_pricing_amount-additional-0-${i}`
                field.name = `${form_prefix}-0-band_pricing_amount-additional-0-${i}`
            }
            i++
        })

        i = 0
        band_method_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-0-band_method-additional-0-${i}`
                field.name = `${form_prefix}-0-band_method-additional-0-${i}`
            }
            i++
        })

        // Don't ask... I don't know why -- KN
        reInitializeBandMethodFields()
        reInitializeBandMethodFields()

        i = 0
        taxed_by_primary_vat_fields.forEach(field => {
            if(i > 0){
                field.id = `id_${form_prefix}-0-taxed_by_primary_vat-additional-0-${i}`
                field.name = `${form_prefix}-0-taxed_by_primary_vat-additional-0-${i}`
            }
            i++
        })
    }
}


// -- //

function getCurrentChargingMethod(){
    return $('[name*="tax_rule_charging_method"]').select2('data')[0].text
}

function getCurrentApplicationMethod(){
    return $('[name*="tax_percentage_rate_application_method"]').select2('data')[0].text
}

function getBandOneType(){
    return  $(`[name*="band_1_type"]`).select2('data')[0].text
}

function getBandTwoType(){
    return  $(`[name*="band_2_type"]`).select2('data')[0].text
}

function reInitializeBandMethodFields(){
    $('.django-select2').each(function () {
        if($(this).attr('name').includes('band_method')){
            $(this).djangoSelect2("destroy")
            $(this).djangoSelect2({
                    dropdownParent: $(this).parent(),
                    width: '100%',
                });
        }
    });
}

function alterHiddenFields(form_divs){

    let existing_tax_div = document.querySelector('.existing-tax')

    let new_tax_text = document.querySelector('.new-tax-text')
    let new_tax_icon = document.querySelector('.new-tax-icon')

    let tax_form_tax_instance_field = document.querySelector('#id_tax_instance')

    let both_fields = document.querySelectorAll('#id_tax_instance, #id_category')
    let region_field = document.querySelector('#id_applicable_region')
    let region_field_label = document.querySelector('label[for=id_applicable_region]')

    if(region_field != null){
        if(region_field.disabled){
            region_field.disabled = false
            region_field.required = true
            region_field_label.classList.add('required')
        } else {
            region_field.disabled = true
            region_field.required = false
            region_field_label.classList.remove('required')
        }
    }

    form_divs.forEach(div => {
        if(!div.classList.contains('d-none')){
            new_tax_text.innerHTML = 'Add New Tax Definition'
            new_tax_icon.classList.add('fa-plus', 'text-success')
            new_tax_icon.classList.remove('fa-minus', 'text-danger')
            existing_tax_div.classList.remove('d-none')
            tax_form_tax_instance_field.disabled = false
            div.classList.add('d-none')
        } else {
            new_tax_text.innerHTML = 'Pick an Existing Tax'
            new_tax_icon.classList.remove('fa-plus', 'text-success')
            new_tax_icon.classList.add('fa-minus', 'text-danger')
            existing_tax_div.classList.add('d-none')
            tax_form_tax_instance_field.disabled = true
            div.classList.remove('d-none')
        }
    })
    toggleRequiredAttributes(both_fields)
}


function alterFieldDisabledAttr(form_fields){

    let tax_percentage_field = document.querySelector('[name$=tax_percentage_rate]')

    form_fields.forEach(field => {
        if(field.parentElement.parentElement.classList.contains('d-none')){
            field.disabled = true
        } else {
            if (field.id == tax_percentage_field.id && field.value != '' &&
                !current_form.innerHTML.includes('Edit') &&
                !current_form.innerHTML.includes('Initial') &&
                current_form.innerHTML.includes('Primary')){
                field.disabled = true
            } else {
                field.disabled = false
            }
        }
    })

}


function enableOnCheckboxCheck(checkbox, field){

    if(checkbox.checked){
        field.disabled = false
    } else {
        field.disabled = true
    }
}


function clearOnCheckboxCheck(checkbox, field){
    let label = field.previousElementSibling

    if(checkbox.checked){
        field.value = ''
        field.required = false
        label.classList.remove('required')
    } else {
        field.required = true
        label.classList.add('required')
    }
}


function updateCheckboxExclusiveWithField(checkbox, field){
    let label = field.previousElementSibling

    if (field.value) {
        checkbox.checked = false
        field.required = true
        label.classList.add('required')
    } else {
        checkbox.checked = true
        field.required = false
        label.classList.remove('required')
    }
}


function isNodeList(nodes) {
    var stringRepr = Object.prototype.toString.call(nodes);

    return typeof nodes === 'object' &&
        /^\[object (HTMLCollection|NodeList|Object)\]$/.test(stringRepr) &&
        (typeof nodes.length === 'number') &&
        (nodes.length === 0 || (typeof nodes[0] === "object" && nodes[0].nodeType > 0));
}


function toggleRequiredAttributes(fields){

    if(!isNodeList(fields)){
        let field = fields
        let encompassing_div = field.parentElement.parentElement
        let label = field.previousElementSibling
        if(encompassing_div.classList.contains('d-none')){
            field.removeAttribute('required')
            label.classList.remove('required')
        } else if (!encompassing_div.classList.contains('d-none')){
            field.setAttribute('required', "")
            label.classList.add('required')
        }
    } else {

        fields.forEach(field => {
            let label = field.previousElementSibling
            let encompassing_div = field.parentElement.parentElement
            if(encompassing_div.classList.contains('d-none')){
                field.required = false
                label.classList.remove('required')
            } else if (!encompassing_div.classList.contains('d-none')){
                field.required = true
                if(label.nodeName == 'LABEL'){
                    label.classList.add('required')
                }
            }
        })
    }
}

function setConditionalRequiredAttributes(fields, selection){

    fields.forEach(field => {
            let label = field.previousElementSibling
            if(selection == ""){
                field.removeAttribute('required')
                if(label != null){
                    label.classList.remove('required')
                }
            } else {
                field.setAttribute('required', "")
                if(label != null){
                    label.classList.add('required')
                }
            }
        })
}

// let submit_button = document.querySelector('.submit')

// submit_button.addEventListener('click', () => {
//     let all_fields = document.querySelectorAll('select, input')
//     all_fields.forEach(field => {
//         field.disabled = false
//     })
// })

let confirm_deletion_button = document.querySelector('.confirm-deletion')
let confirm_deletion_checkbox = document.querySelector('[name*="confirm_checkbox"]')

if(confirm_deletion_button != null){
    confirm_deletion_button.addEventListener('click', () => {
        confirm_deletion_checkbox.checked = true
    })
}


