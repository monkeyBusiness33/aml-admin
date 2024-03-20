var formWrapperEl = $('#mission_amend_timings_form')
var missionLegToAmendField = $('#id_mission_leg_to_amend')
var movementToAmendField = $('#id_movement_to_amend')
var newMovementDateTimeField = $('#id_new_datetime')
var movementChangedBy = $('#id_movement_changed_by')
var movementChangedByLabel = $("label[for='id_movement_changed_by']")


function updateMissionLegToAmend() {
  if (typeof missionLegToAmendField.select2('data')[0] !== "undefined") {
    let flightLegId = missionLegToAmendField.select2('data')[0].id

    // Disable "Movement To Amend" field while "Mission To Amend" is not selected
    if (flightLegId === '') {
      movementToAmendField.prop('disabled', true)
      return
    }

    $("#id_movement_to_amend > option").each(function () {
      let movementToAmend = $(this)
      let movementToAmendFlightLegId = $(this).attr('mission_leg')

      if (movementToAmendFlightLegId !== flightLegId) {
        movementToAmend.prop('disabled', true)
      } else {
        movementToAmend.prop('disabled', false)
      }
      movementToAmendField.prop('disabled', false)

    });
  }
}

function timeUnits( ms ) {
    if ( !Number.isInteger(ms) ) {
        return null
    }
    /**
     * Takes as many whole units from the time pool (ms) as possible
     * @param {int} msUnit - Size of a single unit in milliseconds
     * @return {int} Number of units taken from the time pool
     */
    const allocate = msUnit => {
        const units = Math.trunc(ms / msUnit)
        ms -= units * msUnit
        return units
    }
    // Property order is important here.
    // These arguments are the respective units in ms.
    return {
        // weeks: allocate(604800000), // Uncomment for weeks
        // days: allocate(86400000),
        hours: allocate(3600000),
        minutes: allocate(60000),
        seconds: allocate(1000),
        ms: ms // remainder
    }
}

function newMovementDateTimeChange() {
  let newMovementDateTime = newMovementDateTimeField.val()
  let newMovementDateTimeObj = new Date(newMovementDateTime);

  if (typeof movementToAmendField.select2('data')[0] !== "undefined" && newMovementDateTime) {
    let movementToAmendSelectedEl = movementToAmendField.select2('data')[0].element
    let movementToAmendOriginalDateTime = $(movementToAmendSelectedEl).attr('original_datetime')
    let movementToAmendOriginalDateTimeObj = new Date(movementToAmendOriginalDateTime)

    let movementChangedByMs = (newMovementDateTimeObj - movementToAmendOriginalDateTimeObj);
    let timeUnitsOutput = timeUnits(movementChangedByMs)

    movementChangedBy.val(timeUnitsOutput.hours + ' hours and ' + Math.abs(timeUnitsOutput.minutes) + ' minutes')
    if (movementChangedByMs < 0) {
      movementChangedByLabel.html('Movement <i>Brought Forward</i> By')
    } else {
      movementChangedByLabel.html('Movement <i>Delayed</i> By')
    }

  }
}

formWrapperEl.change(function () {
  updateMissionLegToAmend()
  newMovementDateTimeChange()
});

formWrapperEl.ready(function () {
  updateMissionLegToAmend()
});
