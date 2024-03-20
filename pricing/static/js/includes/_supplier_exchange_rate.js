/**
 * When native pricing unit/application method, supplier converted unit, supplier exchange rate
 * and fuel type (when converting between mass and volume) are specified, display the final exchange
 * rate (including unit, currency and currency division rates) in the Optional Details section
 */

// Select relevant fields that should trigger the update and the result container
let pricingNativeUnitFields = document.querySelectorAll('[id*="-pricing_native_unit"]');
let specificFuelFields = document.querySelectorAll('[id$="-fuel"], [id$="-specific_fuel"]');
let pricingConvertedUnitFields = document.querySelectorAll('[id$="-pricing_converted_unit"]');
let supplierExchangeRateFields = document.querySelectorAll('[id$="-supplier_exchange_rate"]');
let supplierExchangeRateDivs = document.querySelectorAll('div[id$="supplier_final_exchange_rate"]');

pricingNativeUnitFields.forEach(function (el, i) {
  let form_number = el.id.match(/\d+/)[0]
  $(el).on('change', () => showFinalSupplierExchangeRate(form_number));
});

specificFuelFields.forEach(function (el, i) {
  let form_number = el.id.match(/\d+/)[0]
  $(el).on('change', () => showFinalSupplierExchangeRate(form_number));
});

pricingConvertedUnitFields.forEach(function (el, i) {
  let form_number = el.id.match(/\d+/)[0]
  $(el).on('change', () => showFinalSupplierExchangeRate(form_number));
});

supplierExchangeRateFields.forEach(function (el, i) {
  let form_number = el.id.match(/\d+/)[0]
  $(el).on('change', () => showFinalSupplierExchangeRate(form_number));

  // Trigger initial display on page load
  $(el).trigger('change');
});


export default function showFinalSupplierExchangeRate(formNum) {
  // In case of fee creation, there are multiple native units per form, so selection
  // method is different here, and we are posting all fields with value as list
  let nativeUnitFields = document.querySelectorAll(`[id*="-${formNum}-pricing_native_unit"]`);
  nativeUnitFields = Array.from(nativeUnitFields).filter(el => $(el).val());

  let fuelField = specificFuelFields[formNum];
  let convertedUnitField = pricingConvertedUnitFields[formNum];
  let supplierXRField = supplierExchangeRateFields[formNum];
  let finalXRDiv = supplierExchangeRateDivs[formNum];

  if (nativeUnitFields.length && $(convertedUnitField).val() && $(supplierXRField).val() && finalXRDiv) {
    $.ajax({
      type: 'POST',
      url: supplier_xr_url,
      headers: {
        'X-CSRFToken': getCSRFToken(),
        'sessionid': getCookie('sessionid')
      },
      data: {
        'native_unit_pk': nativeUnitFields.map(el => $(el).val()),
        'fuel_pk': $(fuelField).val(),
        'converted_unit_pk': $(convertedUnitField).val(),
        'supplier_xr': $(supplierXRField).val(),
      },
      success: function (resp) {
        if (resp.success === 'true') {
          $(finalXRDiv).html('<ul>');
          resp.rates.forEach((rate, index) => {
            $(finalXRDiv).append(`<li class="small"><b>1 ${rate.from} => ${rate.rate} ${rate.to}</b> ${rate.fuel ? "<br><span class='ms-4'>(" + rate.fuel + ")</span>" : ""}</li>`);
          });
          $(finalXRDiv).append('</ul>');
        } else {
          $(finalXRDiv).html(`<span class="invalid-feedback">${resp.msg}</span>`);
        }

        finalXRDiv.parentElement.hidden = false;
      },
      error: function (resp) {
        $(finalXRDiv).html('');
        finalXRDiv.parentElement.hidden = true;
      }
    });
  } else if (finalXRDiv) {
    $(finalXRDiv).html('');
    finalXRDiv.parentElement.hidden = true;
  }
}
