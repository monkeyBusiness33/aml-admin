// organisation_contact_details_edit.js

emailField = document.querySelector('[id$="email_address"]');
phoneField = document.querySelector('[id$="phone_number"]');
emailSettingCheckboxes = document.querySelectorAll('[id*="address_"]');

// Update display of selected locations
setTimeout(() => {
  let el = document.querySelector('[id$="locations"]');
  $(el).djangoSelect2("destroy");
  $(el).djangoSelect2({
    dropdownParent: $(el).nextSibling,
    width: '100%',
    templateSelection: formatSelected,
  })
}, 200)

function formatSelected(item) {
  let selectionText = item.text.match(/\((?<test>.*)\)$/);
  return $('<span>' + selectionText[1] + '</span>');
}


// Email / phone settings only make sense if email / phone provided
$(emailField).on('input', function () {
  let emailFieldGroup = this.closest('.modal-body').querySelectorAll('[id*="address_"]');
  emailFieldGroup.forEach((settingCheckbox) => {
    settingCheckbox.disabled = !$(this).val();

    if (!$(this).val()) {
      settingCheckbox.checked = false;
    } else if (!Array.from(emailFieldGroup).filter((el) => el.checked).length) {
      this.closest('.modal-body').querySelector('[id*="address_to"]').checked = true;
    }
  })
}).trigger('input');


$(phoneField).on('input', function () {
  this.closest('.modal-body').querySelectorAll('[id*="phone_number_use_for"]').forEach((settingCheckbox) => {
    settingCheckbox.disabled = !$(this).val();

    if (!$(this).val())
      settingCheckbox.checked = false;
  })
}).trigger('input');


// Email settings (TO / CC / BCC) are mutually exclusive
emailSettingCheckboxes.forEach((checkbox) => {
  $(checkbox).on('change', function () {
    if (this.checked) {
      this.closest('.modal-body').querySelectorAll('[id*="address_"]').forEach((otherCheckbox) => {
        if (this.checked && otherCheckbox !== this) otherCheckbox.checked = false;
      });
    } else {
      this.closest('.modal-body').querySelector('[id$="address_to"]').checked = true;
    }
  })
})
