let add_period_buttons = document.querySelectorAll('.new-validity-period-button')
let del_period_buttons = document.querySelectorAll('.delete-period-row')
let revertPeriodsBtns = document.querySelectorAll('.revert-validity-periods-button');
let allDayCheckboxes = document.querySelectorAll('[id*="-valid_all_day"]');


add_period_buttons.forEach(button => {
  button.addEventListener('click', alterValidityPeriodInput)
})

del_period_buttons.forEach(button => {
  button.addEventListener('click', function () {
    this.closest('.validity-period-row').remove()
  });
})

revertPeriodsBtns.forEach(button => {
  button.addEventListener('click', revertToDefaultPeriod)
});

allDayCheckboxes.forEach(checkbox => {
  $(checkbox).on('change', toggleAllDayPeriod);
  $(checkbox).trigger('change');
});


function alterValidityPeriodInput() {
  let form_num = this.closest('[id*="validityAccordion"]').id.match(/\d+/)[0]
  let period_row = document.querySelectorAll(`#validityAccordion-${form_num} .validity-period-row`)
  let row_num = period_row.length

  period_row[row_num - 1].querySelectorAll('.django-select2').forEach(field => $(field).select2('destroy'));
  let new_period_row = period_row[row_num - 1].cloneNode(true);

  let labels = new_period_row.querySelectorAll('label')
  labels.forEach(label => {
    label.remove()
  })

  new_period_row.querySelectorAll('.invalid-feedback').forEach(errorMsg => {
    errorMsg.parentElement.querySelector('input, select').classList.remove('is-invalid');
    errorMsg.remove()
  });

  new_period_row.querySelectorAll('select, input[type="text"]').forEach(period => {
    period.value = "";
    $(period).trigger('change');
  });

  new_period_row.querySelectorAll('.timepicker').forEach(input => {
    $(input).clockTimePicker();
  });

  if (period_row.length == 1) {
    let new_div = document.createElement('div')
    new_div.classList.add('col', 'md-4', 'mb-3', 'deletion-col')
    let delete_period_button = document.createElement('button')
    delete_period_button.classList.add('fas', 'fa-minus', 'text-danger', 'delete-period-row')
    delete_period_button.type = 'button'
    delete_period_button.addEventListener('click', function () {
      this.closest('.validity-period-row').remove()
    })

    new_div.append(delete_period_button)
    new_period_row.append(new_div)
  } else {
    let delete_period_button = new_period_row.querySelector('.delete-period-row')
    delete_period_button.addEventListener('click', function () {
      this.closest('.validity-period-row').remove()
    })
  }

  let insert_before = document.querySelector(`#validityAccordion-${form_num} .insert-before-validity-period`)
  this.parentElement.insertBefore(new_period_row, insert_before)

  alterPeriodFieldNumbering(form_num)
  $(new_period_row.querySelector('[id*="-valid_all_day"]')).on('change', toggleAllDayPeriod);

  let allDayCheckbox = new_period_row.querySelector('[id*="-valid_all_day"]')
  allDayCheckbox.checked = false;
  $(allDayCheckbox).trigger('change');
}


function alterPeriodFieldNumbering(form_num) {
  let periodRows = document.querySelectorAll(
    `#validityAccordion-${form_num} .validity-period-row`);

  if (periodRows.length > 1) {
    periodRows.forEach((row, i) => {
      row.querySelectorAll('select, input').forEach(field => {
        if (i > 0) {
          if (!field.id.includes('additional')) {
            field.id += `-additional-${i}`;
            field.name += `-additional-${i}`;
          } else {
            field.id = field.id.replace(/\d$/i, i.toString());
            field.name = field.name.replace(/\d$/i, i.toString());
          }
        }

        if ($(field).hasClass('django-select2')) reInitializeField(field);
      });
    })
  }
}

function revertToDefaultPeriod() {
  let form_num = this.closest('[id*="validityAccordion"]').id.match(/\d+/)[0]
  let rows = this.closest('.dynamic-section-container').querySelectorAll('.validity-period-row');

  Array.from(rows).slice(1, rows.length).forEach(row => row.remove());
  rows[0].querySelectorAll('select, input[type="text"]').forEach(input => {
    input.value = "";
    $(input).trigger('change');
  });
  let allDayCheckbox = rows[0].querySelector('input[type="checkbox"]');

  allDayCheckbox.checked = false;
  $(allDayCheckbox).trigger('change');

  alterPeriodFieldNumbering(form_num);
}


function toggleAllDayPeriod() {
  let row = this.closest('.row');
  let validFromTimeField = row.querySelector('[id*="-valid_from_time"]');
  let validToTimeField = row.querySelector('[id*="-valid_to_time"]');

  if (this.checked) {
    validFromTimeField.value = "00:00";
    validFromTimeField.disabled = true;
    validToTimeField.value = "23:59";
    validToTimeField.disabled = true;
  } else {
    validFromTimeField.disabled = false;
    validToTimeField.disabled = false;
  }
}


function reInitializeField(field) {
  $(field).djangoSelect2({
    dropdownParent: $(field).parent(),
    width: '100%',
  });
}
