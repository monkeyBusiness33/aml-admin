let fileField = document.querySelector('#id_pricing_csv_file');
let importBtns = document.querySelectorAll('.fuel-pricing-market-import-btn');
let ipaReconciliationModalElement = document.querySelector('#reconcile-ipas-modal');
let ipaReconciliationModalBody = ipaReconciliationModalElement.querySelector('.modal-body')
let ipaReconciliationModal = new bootstrap.Modal(ipaReconciliationModalElement);


Array.from(importBtns).forEach(function (btn) {
  btn.addEventListener('click', function (e) {
    e.preventDefault();
    importPricingFile(e.target);
  });
});


function importPricingFile(target) {
  let form = target.closest('form');
  let formErrorDiv = form.querySelector('#fuel_market_pricing_csv_importer_form_errors');

  let isError = false;

  // Reset error markings on form fields
  $('.is-invalid').each(function () {
    $(this).removeClass('is-invalid');
  });
  $('.has-error').each(function () {
    $(this).removeClass('has-error form-control');
  });
  $('.input-error').each(function () {
    $(this).remove();
  });

  $(':input[required]:visible').each(function () {
    if (!($(this).val())) {
      $(this).addClass('is-invalid');
      isError = true;
    }
  });

  formErrorDiv.innerHTML = '';

  if (!isError) {
    if (!document.querySelector('#id_changes_to_fees_0').checkValidity()) {
      isError = true
      document.querySelector('#id_changes_to_fees_0').reportValidity()
    }
  }

  if (!isError) {
    if (!document.querySelector('#id_changes_to_taxes_0').checkValidity()) {
      isError = true
      document.querySelector('#id_changes_to_taxes_0').reportValidity()
    }
  }

  if (isError) return;

  // On main form submission, clear modal
  if (target.id === 'fuel-pricing-market-import-main-form-btn') {
    $(ipaReconciliationModalBody).html(null);
  }

  target.disabled = true;
  target.innerText = 'Importing...';
  let formData = new FormData(form);

  // On modal form submission, set appropriate flag
  if (target.id === 'ipa-modal-save-btn') {
    formData.append("ipa_confirmed", "True");
  }

  $.ajax({
    type: 'POST',
    url: '',
    headers: {
      'X-CSRFToken': getCSRFToken(),
      'sessionid': getCookie('sessionid')
    },
    data: formData,
    contentType: false,
    processData: false,

    success: function (response) {
      let ipaFormHtml = response['ipa_form_html'];

      if (ipaFormHtml) {
        $(ipaReconciliationModalBody).html(ipaFormHtml);
        reInitializeSelect2();
        ipaReconciliationModal.show();
      } else {
        ipaReconciliationModal.hide();
        if (response['redirect_url']) {
          window.location.href = response['redirect_url']
        }
      }
    },
    error: function (response) {
      if (response.responseJSON && response.responseJSON.errors) {
        errors = response.responseJSON.errors
        let modalError = false;

        for (error in errors) {
          for (const [key, value] of Object.entries(form)) {
            if (typeof value.name !== 'undefined' && value.name.includes(error)) {
              let fg = $($(value.closest('.form-group')));
              errors[error].forEach(function (el) {
                fg.append('<p class="input-error sup small mt-4 mb-0">' + errors[error] + '</p>');
              });

              if (value.name.includes('ipa_org')) {
                ipaReconciliationModal.show();
                modalError = true;
              }
            }
          }

          if (error == '__all__') {
            formErrorDiv.innerHTML += `<div class="text-danger">${errors[error]}</div>`;
          }
        }

        if (!modalError) {
          ipaReconciliationModal.hide();
        }
      } else {
        let error_msg = 'File submission failed, possibly due to local changes to the file' +
          ' after it has been attached. Please try reattaching the file or refreshing the page.'
        formErrorDiv.innerHTML += `<div class="text-danger">${error_msg}</div>`;
      }
    }
  }).always(function (response) {
    target.disabled = false;
    target.innerText = 'Import';

    load_tooltips();
  })
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
