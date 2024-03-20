let dateTimeGracePeriodEnd = new Date(retrospective_grace_period * 1000);
let dateTimeNow = new Date(retrospective_datetime_now * 1000).getTime();
let timeGracePeriodRemaining = dateTimeGracePeriodEnd - dateTimeNow;

let x = setInterval(function () {
  timeGracePeriodRemaining = timeGracePeriodRemaining - 1000

  // Time calculations for days, hours, minutes and seconds
  // var days = Math.floor(distance / (1000 * 60 * 60 * 24));
  // var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  var minutes = Math.floor((timeGracePeriodRemaining % (1000 * 60 * 60)) / (1000 * 60));
  var seconds = Math.floor((timeGracePeriodRemaining % (1000 * 60)) / 1000);

  document.getElementById("retrospective_sfr_timer").innerHTML = minutes + "m " + seconds + "s ";

  // If the count-down is finished, write some text
  if (timeGracePeriodRemaining <= 0) {
    document.getElementById("retrospective_sfr_timer").innerHTML = "EXPIRED";

    setTimeout(() => {
      location.reload();
    }, 5000);

  }
}, 1000);
