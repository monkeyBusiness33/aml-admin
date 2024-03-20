// File with global scope JS. This file can be included into all pages
// even modal, functions should support multiple executions on same page


function getCookie(name) {
  // Get CSRF Token = getCookie('csrftoken')
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    let cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      let cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}


function getCSRFToken() {
  let csrftoken = getCookie('csrftoken');
  if (csrftoken == null) {
    csrftoken = $('input[name=csrfmiddlewaretoken]').val();
  }
  return csrftoken;
}


var swalWithBootstrapButtons = Swal.mixin({
  customClass: {
    confirmButton: 'btn btn-primary me-3',
    cancelButton: 'btn btn-gray'
  },
  buttonsStyling: false
});


function loadVanillaJsDatePicker(e) {
  // Datepicker
  let datePickers = [].slice.call(d.querySelectorAll('[data-datepicker]'))
  datePickers.map(function (el) {
    return new Datepicker(el, {
      buttonClass: 'btn',
      format: 'yyyy-mm-dd',
      autohide: true,
    });
  })

}


$(document).ready(function () {
  loadVanillaJsDatePicker()

  // Support for maxLength attr for numeric inputs
  $(':input[type="number"]').on('propertychange input', function () {
    if (typeof this.maxLength !== "undefined" && this.maxLength > 0) {
      if (this.value.length > this.maxLength) this.value = this.value.slice(0, this.maxLength);
    }
  });

    // Disable forms double submission
    $('form').submit(function(){
      $(this).find(':submit').prop('disabled', true);
    });

    // Initialize timepicker by class name
    $('.timepicker').clockTimePicker({});

    $('[data-toggle="toggle"]').each(function () {
      $(this).bootstrapToggle()
    });

    if ($('.modal-body .django-select2').length) {
        setTimeout(() => {
            $('.modal-body .django-select2').each((i, el) => {
                $(el).djangoSelect2({
                    dropdownParent: el.closest('.modal-body'),
                    width: '100%'
                });
            });
        }, 150);
    }

    // Reset field 'is-invalid' state
    $('.is-invalid').focusin(function(){
        $(this).removeClass('is-invalid')
    })

    $('.generation-button').click(function(){
        // Function to lock and animate S&F Request "Get PDF" Download button
        let button = this
        let elements = $(button).find('.fas')

        setTimeout(function() {
                $(button).removeClass('disabled');
                $(button).attr('disabled', false);
                elements.removeClass('fa-spinner fa-spin');
                elements.addClass('fa-file-pdf');
            }, 4500);

        $(elements).removeClass('fa-file-pdf');
        $(elements).addClass('fa-spinner fa-spin');
        $(this).addClass('disabled');
    });

    // "Generic multi-row" formset
    function formset_delete_button_state() {
        var remainForms = $('.formset_row:not(.to_delete,.d-none)').length
        if (remainForms === 1) {
            var btn = $('.formset_row:not(.to_delete,.d-none)').find('.formset_row_del_btn')
            $(btn).prop('disabled', true);
        } else {
            $('.formset_row_del_btn').each(function (index, btn) {
                let btnProtectionFlag = $(btn).data('persistent') || false;
                if (!btnProtectionFlag) {
                    $(this).prop('disabled', false);
                }
            });
        }
    }
    formset_delete_button_state()

    $("#formset_row_add_btn").click(function () {
        var addRowsBy = $(this).attr('data-add-by') || 1;
        $(".formset_row.d-none:not(.to_delete)").slice(0, addRowsBy).removeClass("d-none");
        var remainForms = $('.formset_row.d-none:not(.to_delete)').length
        if (remainForms === 0) {
            $(this).prop('disabled', true);
        }
        formset_delete_button_state()
    });

    $(".formset_row_del_btn").click(function () {
        var FormPrefix = $(this).attr('data-form-pre')
        $('#id_' + FormPrefix + '-DELETE').prop('checked', true);
        $("#id_" + FormPrefix + '_card').first().addClass("d-none to_delete");
        formset_delete_button_state()
    });


    // Textarea input counter
    $('input[type=text], textarea').keyup(function () {
        maxlength = $(this).attr('maxlength')
        var text_length = $(this).val().length;
        var text_remaining = maxlength - text_length;
        $(this).next('.textarea-char-counter').html(text_length + ' / ' + maxlength);

        if (text_remaining > 498) {
            $(this).next('.textarea-char-counter').removeClass('bg-warning bg-danger').addClass("bg-gray-600");
        }
        if (text_remaining < 50) {
            $(this).next('.textarea-char-counter').removeClass('bg-gray-600 bg-danger').addClass("bg-warning");
        }
        if (text_remaining < 10) {
            $(this).next('.textarea-char-counter').removeClass('bg-gray-600 bg-warning').addClass("bg-danger");
        }
    });

    $('.copy-to-clipboard').click(function (element) {
        var html = element.target
        var value = $(html).data('copy-value')
        var $temp = $("<input>");
        $("body").append($temp);
        $temp.val(value).select();
        document.execCommand("copy");
        $temp.remove();
    });

  $('.exclusive-field').on('right_now change click load', function () {
    // exclusive-field - enables "exclusive field" functionality for a field
    // exclusive-field-required - makes at least one field in group required
    // data-exclusive-field-group - exclusive fields group

    let fieldHasValue = false

    let exclusiveFieldGroup = $(this).data('exclusive-field-group')
    let allFieldsInGroup = $('[data-exclusive-field-group=' + exclusiveFieldGroup + ']')

    if ($(this).is(':checkbox')) {
      fieldHasValue = $(this).is(':checked')
      if (fieldHasValue) {
        allFieldsInGroup.not($(this)).prop('checked', false)
      }
    } else {

      allFieldsInGroup.each(function (index, field) {

        if ($(field).val() !== '') {
          fieldHasValue = true
          allFieldsInGroup.not($(field)).prop('disabled', true)
          allFieldsInGroup.not($(field)).val(null)

          allFieldsInGroup.not($(field)).each(function (i, f) {
            $(f).attr('required', false)
            $("label[for='" + $(f).attr('id') + "']").removeClass('required')
          })

        }

        if (!fieldHasValue) {
          allFieldsInGroup.prop('disabled', false)
          if ($(field).hasClass('exclusive-field-required')) {
            allFieldsInGroup.each(function (i, f) {
            $(f).attr('required', true)
            $("label[for='" + $(f).attr('id') + "']").addClass('required')
          })
          }
        }

      });
    }

  }).triggerHandler("right_now");

    $('.auto-round-to-step').change(roundToStep);
});


// Export Servicing & Fueling Request Data Modal
// missions_export_modal = $('#missions_export')
// if (missions_export_modal.length) {
//   missions_export_modal.submit(function () {
//     is_invalid = $('div.is-invalid')
//     is_invalid.remove()
//
//     setTimeout(function () {
//       is_error = $('div.is-invalid').length
//       if (is_error === 0 || !is_error) {
//         $('.modal').modal("hide")
//       }
//     }, 1000);
//
//   });
// }

function roundToStep() {
  // Round a numerical input field to appropriate number of decimal places based on step property
  if (!this.value || isNaN(this.value)) return;

  let inputValue = new Decimal(this.value);
  let stepValue = new Decimal(this.step);
  this.value = inputValue.toDecimalPlaces(stepValue.dp());
}
