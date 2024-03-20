let upliftQtyField = document.querySelector('[id$="uplift_qty"]');
let upliftUomField = document.querySelector('[id$="uplift_uom"]');

let aircraftField = $('#id_form-0-aircraft')
let aircraftFieldLabel = $("label[for='" + aircraftField.attr('id') + "']");
let aircraftTypeField = $('#id_form-0-aircraft_type')
let aircraftTypeFieldLabel = $("label[for='" + aircraftTypeField.attr('id') + "']");
let flightTypeField = $('#id_form-0-flight_type')
let commercialPrivateToggle = $('#id_form-0-is_private')
let calculateBtn = $('#calculate_pricing_scenario_btn');
let overrideXrBtn = $('#override-xr-btn');
let resultsHeader = $('#supplier_fuel_pricing_header');
let resultsDiv = $('#fuel-pricing-results');

let fuelTakenToggle = document.querySelector('[id$="is_fuel_taken"]');
let defuelingToggle = document.querySelector('[id$="is_defueling"]');
let multiVehicleToggle = document.querySelector('[id$="is_multi_vehicle"]');

flightTypeField.prop('required', true);

// Reset and disable (mutually exclusive) Aircraft / Aircraft Type fields when the other is selected
function resetAircraftTypeField() {
  if (aircraftField.val()) {
    aircraftTypeField.val(null);
    aircraftTypeField.prop('disabled', true);
    $('#select2-id_form-0-aircraft_type_fuel_pricing_calculation-container').prop('title', 'Select Aircraft Type');
    $('#select2-id_form-0-aircraft_type_fuel_pricing_calculation-container').text('Select Aircraft Type');
  } else {
    aircraftTypeField.prop('disabled', false);
  }
}

function resetAircraftField() {
  if (aircraftTypeField.val()) {
    aircraftField.val(null);
    aircraftField.prop('disabled', true);
    $('#select2-id_form-0-aircraft_fuel_pricing_calculation-container').prop('title', 'Select Aircraft');
    $('#select2-id_form-0-aircraft_fuel_pricing_calculation-container').text('Select Aircraft');
  } else {
    aircraftField.prop('disabled', false);
  }
}

aircraftField.on('change', function () {
  resetAircraftTypeField();
});

aircraftTypeField.on('change', function () {
  resetAircraftField();
});

// Fix Commercial / Private toggle on 'Private' when Flight Type is MIL or Training
flightTypeField.on('change', function () {
  let flightType = flightTypeField.val();

  if (['M', 'T'].includes(flightType)) {
    if (!commercialPrivateToggle.prop('checked')) {
      commercialPrivateToggle.prop('checked', true);
      commercialPrivateToggle.parent('.toggle').removeClass('off');
    }

    // Only disable using class, otherwise the value is dropped from submitted form data
    commercialPrivateToggle.parent('.toggle').addClass('disabled');
  } else {
    commercialPrivateToggle.parent('.toggle').removeClass('disabled');
  }
});

fuelTakenToggle.addEventListener('change', updateAdvancedOptions);
defuelingToggle.addEventListener('change', updateAdvancedOptions);
multiVehicleToggle.addEventListener('change', updateAdvancedOptions);

function runCalculation(target, isRerun=false) {
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

  $('.django-select2[required]').each(function () {
    if (!($(this).val())) {
      $(this).next().find('.select2-selection').addClass('has-error form-control is-invalid');
      isError = true;
    }
  });

  if (!document.querySelector('#id_form-0-uplift_qty').checkValidity()) {
    isError = true
    document.querySelector('#id_form-0-uplift_qty').reportValidity()
  }

  if (isError) return;

  let target_btn = $(target).closest('button');
  let overrideToggle = document.querySelector('#id_form-0-override_xr');
  let overrideXr = overrideToggle.checked;

  let xrModalElement = document.querySelector('#modal-override-xr');
  let xrModalBody = xrModalElement.querySelector('.modal-body')
  let xrModal = new bootstrap.Modal(xrModalElement);

  // Ensure the override fields are removed if not needed before submitting form
  if (!overrideXr || !isRerun) {
    $(xrModalBody).html(null);
  }

  let serializedData = $(target).closest('form').serializeArray()
  serializedData.push({name: 'is_rerun', value: Number(isRerun)});
  serializedData.push({name: 'context', value: context});
  serializedData.push({name: 'airport', value: airport});

  target_btn.prop('disabled', true);
  target_btn.text('Calculating');

  $.ajax({
    type: 'POST',
    url: '/ops/suppliers/fuel_cost_estimate/',
    data: serializedData,

    success: function (response) {
      resultsHeader.removeAttr('hidden');
      resultsDiv.html(response['results']);
      let xrForm = response['currency_xr_form'];

      if (overrideXr && xrForm && !isRerun) {
        $(xrModalBody).html(xrForm);
        xrModal.show();
      } else {
        $(xrModalBody).html(null);
      }
    },
    error: function (response) {
      if (response.responseJSON && response.responseJSON.errors) {
        errors = response.responseJSON.errors
        console.log(errors);
        let form = $('#fuel-pricing-calculation-form');

        for (error in errors) {
          for (const [key, value] of Object.entries(form[0])) {
            if (typeof value.name !== 'undefined' && value.name.includes(error)) {
              let fg = $($(value.closest('.form-group')));
              errors[error].forEach(function (el) {
                fg.append('<p class="input-error sup small mb-0">' + errors[error] + '</p>');
              });

              if (value.name.includes('new_xr_')) {
                xrModal.show();
              }

              if (value.name === 'src_calculation_id') {
                let override_error_section = $('#override-error-section');
                override_error_section.append('<p class="input-error sup small mb-0">' + errors[error] + '</p>');
                xrModal.show();
              }
            }
          }
        }
      }
    }
  }).always(function (response) {
    target_btn.prop('disabled', false);
    target_btn.text(metacontext['btn_text']);

    load_tooltips();
  })
}

calculateBtn.on('click', function (e) {
  e.preventDefault();
  runCalculation(e.target);
});

overrideXrBtn.on('click', function (e) {
  e.preventDefault();
  runCalculation(e.target, true);
});


function setAccordionArrow(button){
    if(button.parentElement.parentElement.classList.contains('collapsed')){
        button.classList.add('accordion-closed')
        button.classList.remove('accordion-open')
    } else {
        button.classList.add('accordion-open')
        button.classList.remove('accordion-closed')
    }
}

function updateAdvancedOptions() {
  if (!fuelTakenToggle.checked) {
    defuelingToggle.disabled = false;
    multiVehicleToggle.checked = false;
    multiVehicleToggle.disabled = true;
    upliftQtyField.disabled = true;
    upliftUomField.disabled = true;
  } else {
    defuelingToggle.checked = false;
    defuelingToggle.disabled = true;
    multiVehicleToggle.disabled = false;
  }

  if (defuelingToggle.checked) {
    fuelTakenToggle.checked = false;
    fuelTakenToggle.disabled = true;
    upliftQtyField.disabled = true;
    upliftUomField.disabled = true;
  } else {
    fuelTakenToggle.disabled = false;
  }

  if (fuelTakenToggle.checked && !defuelingToggle.checked) {
    upliftQtyField.disabled = false;
    upliftUomField.disabled = false;
  }
}

let accordion_arrows = document.querySelectorAll('.accordion-arrow')
accordion_arrows.forEach(arrow => {
    setAccordionArrow(arrow)

    let accordion_button = arrow.parentElement.parentElement
    accordion_button.addEventListener('click', function(){
        setAccordionArrow(arrow)
    })
})


resetAircraftField();
resetAircraftTypeField();
updateAdvancedOptions();
