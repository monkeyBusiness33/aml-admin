let emailField = document.querySelectorAll('[id$="-email_address"]');
let phoneField = document.querySelectorAll('[id$="-phone_number"]');
let emailSettingCheckboxes = document.querySelectorAll('[id*="-address_"]');
let deleteBtns = document.querySelectorAll('.delete-form-section');
let addRowBtn = document.querySelector('#add_contact_details_btn');

// Update display of selected locations
setTimeout(() => {
  document.querySelectorAll('[id$="-locations"]').forEach((el) => {
    $(el).djangoSelect2("destroy");
    $(el).djangoSelect2({
      dropdownParent: $(el).nextSibling,
      width: '100%',
      templateSelection: formatSelected,
    })
  })
}, 500)

function formatSelected(item) {
  let selectionText = item.text.match(/\((?<test>.*)\)$/);
  return $('<span>' + selectionText[1] + '</span>');
}

// Email / phone settings only make sense if email / phone provided
emailField.forEach((field) => {
  $(field).on('input', function () {
    let emailFieldGroup = this.closest('.stacked-input').querySelectorAll('[id*="-address_"]');
    emailFieldGroup.forEach((settingCheckbox) => {
      settingCheckbox.disabled = !$(this).val();

      if (!$(this).val()) {
        settingCheckbox.checked = false;
      } else if (!Array.from(emailFieldGroup).filter((el) => el.checked).length) {
        this.closest('.stacked-input').querySelector('[id*="address_to"]').checked = true;
      }
    })
  })

  $(field).trigger('input');
})

phoneField.forEach((field) => {
  $(field).on('input', function () {
    this.closest('.stacked-input').querySelectorAll('[id*="phone_number_use_for"]').forEach((settingCheckbox) => {
      settingCheckbox.disabled = !$(this).val();

      if (!$(this).val())
        settingCheckbox.checked = false;
    })
  })

  $(field).trigger('input');
})

// Email settings (TO / CC / BCC) are mutually exclusive
emailSettingCheckboxes.forEach((checkbox) => {
  $(checkbox).on('change', function () {
    if (this.checked) {
      this.closest('.stacked-input-element').querySelectorAll('input').forEach((otherCheckbox) => {
        if (this.checked && otherCheckbox !== this) otherCheckbox.checked = false;
      });
    } else {
      this.closest('.stacked-input-element').querySelector('[id$="address_to"]').checked = true;
    }
  })
})

// New row addition
$(addRowBtn).click(function () {
  $(".form.d-none").first().removeClass("d-none");
  let remainingHiddenFormCount = $('.form.d-none').length
  if (remainingHiddenFormCount === 0) $(this).prop('disabled', true);
  deleteBtnState();
});

// Row deletion
$(deleteBtns).click(function () {
  let row = this.closest('.form');
  row.querySelector('input[id$="DELETE"]').checked = true;
  row.remove();

  // Update numbers (so the positions stay the same on error)
  document.querySelectorAll('.form').forEach((form, i) => {
    form.querySelectorAll('[id*="formset-"]').forEach((field) => {
      field.id = field.id?.replace(/formset-\d+/i, `formset-${i}`);
      field.name = field.name?.replace(/formset-\d+/i, `formset-${i}`);
    })
  })

  deleteBtnState();
});

function deleteBtnState() {
  let remainingVisibleFormCount = $('.form:not(.d-none)').length
  if (remainingVisibleFormCount === 1) {
    deleteBtns.forEach((btn) => btn.disabled = true);
  } else {
    deleteBtns.forEach((btn) => btn.disabled = false);
  }
}
