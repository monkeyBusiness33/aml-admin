const datePickerForm = $('#daily-schedule-date-form')
const datePicker = $('#id_date')

// Buttons
const dateBackwardBtn = $('#date-backward')
const dateTodayBtn = $('#date-today')
const dateForwardBtn = $('#date-forward')

datePickerForm.change(function () {
  datePickerForm.submit();
});

dateTodayBtn.click(function () {
  let todayDate = new Date().toISOString().split('T')[0]
  datePicker.val(todayDate)
  datePickerForm.submit();
});


function datePickerChangeDate(direction) {
  // Change date by 1 day forward or backwards
  let offset = (24*60*60*1000)
  let currentDateRaw = datePicker.val()
  let currentDateObj = new Date(currentDateRaw)

  if (direction === 'backward') {
    currentDateObj.setTime(currentDateObj.getTime() - offset);
  } else {
    currentDateObj.setTime(currentDateObj.getTime() + offset);
  }

  let newDate = currentDateObj.toISOString().split('T')[0]
  datePicker.val(newDate)
  datePickerForm.submit();
}


dateBackwardBtn.click(function () {
  datePickerChangeDate('backward')
});

dateForwardBtn.click(function () {
  datePickerChangeDate('forward')
});

