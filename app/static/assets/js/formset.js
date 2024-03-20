// New implementation of formset functionality which supports multiple formsets on the same page
// Used in:
// - handling/templates/handling_request_payload_modal.html

function formset_delete_button_state(formset) {
    let active_forms = $(formset).find('.formset-row:not(.to_delete,.d-none)').length
    if (active_forms === 1) {
        let btn = formset.find('.formset-row:not(.to_delete,.d-none)').find('.formset-row-del-btn')
        $(btn).prop('disabled', true);
    } else {
        $(formset).find('.formset-row:not(.to_delete,.d-none)').find('.formset-row-del-btn').each(function (index, btn) {
            let btnProtectionFlag = $(btn).data('persistent') || false;
            if (btnProtectionFlag) {
                $(this).prop('disabled', true);
            } else {
                $(this).prop('disabled', false);
            }
        });
    }
}

$('div.formset-section').each(function() {
    let formset = $(this)
    formset_delete_button_state(formset)
})

$(document).change(function() {
    let formset = $(this)
    formset_delete_button_state(formset)
})

function formset_add_button_state(formset) {
    let addRowsBy = $(this).attr('data-add-by') || 1;
    formset.find('.formset-row.d-none:not(.to_delete)').slice(0, addRowsBy).removeClass("d-none");
    let remainForms = formset.find('.formset-row.d-none:not(.to_delete)').length
    if (remainForms === 0) {
        formset.find('.formset-row-add-btn').prop('disabled', true);
    } else {
        formset.find('.formset-row-add-btn').prop('disabled', false);
    }
}


$(".formset-row-add-btn").click(function () {
    let formset = $(this).parents('div.formset-section')
    formset_add_button_state(formset)
});

$(".formset-row-del-btn").click(function () {
    let FormPrefix = $(this).attr('data-form-pre')
    let formset = $(this).parents('div.formset-section')
    $('#id_' + FormPrefix + '-DELETE').prop('checked', true);
    $("#id_" + FormPrefix + '_card').first().addClass("d-none to_delete");
    formset_delete_button_state(formset)
});