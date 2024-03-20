// fuel_agreement_create.js

/**
 * Reorder elements of source_doc_file field (it seems that doing this properly,
 * by overwriting widget template, is much more of a pain).
 */
function valid_ufn_trigger(e) {
  // These fields are not available in Edit view
  if (mode === 'edit') return;

  validToField = $("#id_end_date");
  validToFieldLabel = $("label[for='" + validToField.attr('id') + "']");
  validUFNChecked = $("#id_valid_ufn").is(':checked')
  if (validUFNChecked) {
    validToField.val(null).trigger('change')
    validToField.prop('disabled', true)
    validToField.prop('required', false)
    validToFieldLabel.removeClass('required');
    validToField.removeClass('is-invalid');
  } else {
    validToField.prop('disabled', false)
    validToField.prop('required', true)
    validToFieldLabel.addClass('required');
  }
}

function reorderFileWidget() {
  sourceDocFileField = $("#id_source_doc_file");
  sourceDocFileWidget = sourceDocFileField.parent();
  sourceDocFileField.detach();
  sourceDocFileWidget.contents()
    .filter((_, el) => el.nodeType === 3)
    .slice(2,).remove();
  sourceDocFileField.insertAfter(sourceDocFileWidget.children('label'));
}

function updateFileFields() {
  sourceDocNameField = $('#id_source_doc_name');
  sourceDocFileField = $('#id_source_doc_file');

  if (sourceDocNameField.val() || sourceDocFileField.val() || sourceDocFileField.parent().has('a').length) {
    sourceDocNameField.prop('required', true);
    sourceDocNameField.siblings('label').addClass('required');
    sourceDocFileField.siblings('label').addClass('required');

    if (!sourceDocFileField.parent().has('a').length) {
      sourceDocFileField.prop('required', true);
    }
  } else {
    sourceDocNameField.prop('required', false);
    sourceDocNameField.siblings('label').removeClass('required');
    sourceDocFileField.prop('required', false);
    sourceDocFileField.siblings('label').removeClass('required');
  }
}

function prepaymentTrigger() {
  paymentTermsValueField = $("#id_payment_terms_unit_count");
  paymentTermsUnitField = $("#id_payment_terms_time_unit");
  isPrepayment = $("#id_is_prepayment").is(':checked');

  if (isPrepayment) {
    paymentTermsValueField.val(null);
    paymentTermsValueField.prop('disabled', true);
    paymentTermsValueField.prop('required', false);
    paymentTermsUnitField.val(null).trigger('change');
    paymentTermsUnitField.prop('disabled', true);
    paymentTermsUnitField.prop('required', false);
    paymentTermsValueField.siblings('label').removeClass('required');
  } else {
    paymentTermsValueField.prop('disabled', false);
    paymentTermsValueField.prop('required', true);
    paymentTermsUnitField.prop('disabled', false);
    paymentTermsUnitField.prop('required', true);
    paymentTermsValueField.siblings('label').addClass('required');
  }
}


function depositRequiredTrigger() {
  let depositRequiredCheckbox = $("#id_deposit_required");
  let depositAmountField = $("#id_deposit_amount");
  let depositCurrencyField = $("#id_deposit_currency");
  let depositRequired = depositRequiredCheckbox.is(':checked');

  if (!depositRequired) {
    depositAmountField.val(null);
    depositAmountField.prop('disabled', true);
    depositAmountField.prop('required', false);
    depositAmountField.siblings('label').removeClass('required');
    depositCurrencyField.val(null).trigger('change');
    depositCurrencyField.prop('disabled', true);
    depositCurrencyField.prop('required', false);
    depositCurrencyField.siblings('label').removeClass('required');
  } else {
    depositAmountField.prop('disabled', false);
    depositAmountField.prop('required', true);
    depositAmountField.siblings('label').addClass('required');
    depositCurrencyField.prop('disabled', false);
    depositCurrencyField.prop('required', true);
    depositCurrencyField.siblings('label').addClass('required');
  }
}

$("#id_valid_ufn").change(function () {
  valid_ufn_trigger();
});

$("#id_source_doc_name").keyup(function () {
  updateFileFields();
});

$("#id_source_doc_file").change(function () {
  updateFileFields();
});

$("#id_is_prepayment").change(function () {
  prepaymentTrigger();
});

$("#id_deposit_required").change(function () {
  depositRequiredTrigger();
});

waitForElement(`.toggle-group [for*="id_valid_ufn"]`).then(() => {
  valid_ufn_trigger();
  reorderFileWidget();
  updateFileFields();
  prepaymentTrigger();
  depositRequiredTrigger();
});


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
