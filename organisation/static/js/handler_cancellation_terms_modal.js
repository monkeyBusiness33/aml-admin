function processTermsFormsetRow() {
  $('.formset-row').each(function (i, obj) {
    var rowPrefix = $(obj).data('formset-row-prefix')

    var serviceFieldId = '#id_' + rowPrefix + '-penalty_specific_service'
    var serviceField = $(serviceFieldId)

    var penaltyPercentageId = '#id_' + rowPrefix + '-penalty_percentage'
    var penaltyPercentageField = $(penaltyPercentageId)

    var penaltyAmountId = '#id_' + rowPrefix + '-penalty_amount'
    var penaltyAmountField = $(penaltyAmountId)

    var penaltyAmountCurrencyId = '#id_' + rowPrefix + '-penalty_amount_currency'
    var penaltyAmountCurrencyField = $(penaltyAmountCurrencyId)

    function processFieldsAttrs() {
      if (penaltyPercentageField.val() !== '' || penaltyAmountField.val() !== '' || penaltyAmountCurrencyField.select2('data')[0].id !== '' || serviceField.select2('data')[0].id !== '') {
        penaltyPercentageField.attr('required', true)
        penaltyAmountField.attr('required', true)
        penaltyAmountCurrencyField.attr('required', true)

        if (penaltyPercentageField.val() !== '') {
          penaltyAmountField.attr('required', false)
          penaltyAmountCurrencyField.attr('required', false)
        }

        if (penaltyAmountField.val() !== '' || penaltyAmountCurrencyField.select2('data')[0].id !== '') {
          penaltyPercentageField.attr('required', false)
        }
      } else {
        penaltyPercentageField.attr('required', false)
        penaltyAmountField.attr('required', false)
        penaltyAmountCurrencyField.attr('required', false)
      }
    }

    processFieldsAttrs()

    function disableAmountFields(disable) {
      if (disable) {
        penaltyAmountCurrencyField.val(null)
        penaltyAmountField.val(null)
      }
      penaltyAmountField.prop('disabled', disable);
      penaltyAmountCurrencyField.prop('disabled', disable);
    }

    function disablePercentageField(disable) {
      if (disable) {
        penaltyPercentageField.val(null)
      }
      penaltyPercentageField.prop('disabled', disable);
    }

    if (penaltyPercentageField.val() !== '') {
      disableAmountFields(true)
    } else {
      disableAmountFields(false)
    }

    if (penaltyAmountField.val() !== '' || penaltyAmountCurrencyField.select2('data')[0].id !== '') {
      disablePercentageField(true)
    } else {
      disablePercentageField(false)
    }

  });
}

cancellation_terms_section = $('#cancellation_terms_section')

cancellation_terms_section.ready(function () {
  processTermsFormsetRow()
});

cancellation_terms_section.change(function () {
  processTermsFormsetRow()
});
