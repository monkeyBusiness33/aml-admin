"use strict";


d.addEventListener("DOMContentLoaded", function (event) {
  let calendarEl = d.getElementById('missions_calendar');
  let now = new Date();

  if (calendarEl) {
    let calendar = new FullCalendar.Calendar(calendarEl, {
      views: {
        timeGrid: {
          type: 'timeGridWeek',
          expandRows: true,
          dayHeaderFormat: { weekday: 'short', month: '2-digit', day: '2-digit', omitCommas: true }

        }
      },
      timeZone: 'UTC',
      slotLabelFormat: {hour: '2-digit', minute: '2-digit', hour12: false},
      locale: 'en-GB',
      expandRows: true,
      selectable: false,
      initialView: 'dayGridMonth',
      themeSystem: 'bootstrap',
      initialDate: now,
      eventDisplay: 'block',
      editable: false,
      allDaySlot: false,
      events: {
        url: missions_json_url,
        extraParams: function () {
          // function checkboxValue() {
          //   let checkbox_el = $('#currentOnlyCheckbox')
          //   if (typeof checkbox_el.html() === "undefined" || checkbox_el.is(':checked')) {
          //     console.log('checked')
          //     return true
          //   } else {
          //     console.log('not checked')
          //     return false
          //   }
          // }
          //
          // return {
          //   only_current: checkboxValue()
          // };
        }
      },
      stickyFooterScrollbar: 'false',
      height: 'auto',
      buttonIcons: {
        prev: 'chevron-left',
        next: 'chevron-right',
      },
      customButtons: {
        requestsListButton: {
          text: 'Missions List',
          click: function () {
            window.location.href = missions_list_url;
          }
        },
        createHandlingRequestButton: {
          text: 'Add Mission',
          click: function () {
            window.location.href = missions_create_url;
          }
        },
        // currentOnlyButton: {
        //   text: '',
        //   click: function () {
        //   }
        // }
      },
      headerToolbar: {
        left: 'title',
        right: 'requestsListButton createHandlingRequestButton dayGridMonth,timeGridWeek prev,today,next'
      },
      eventContent: function (info) {
        return {html: info.event.title};
      },
      dateClick: function (d) {
      },
      eventClick: function (info, element) {
        info.jsEvent.preventDefault();
        if (info.event.url) {
          window.open(info.event.url);
        }
      },
      eventMouseEnter: function (info) {
        let tooltip = new bootstrap.Tooltip(info.el, {
          title: info.event.extendedProps.tooltip,
          html: true,
          placement: 'top',
          trigger: 'hover',
          container: 'body'
        });
        tooltip.show()
      },
      eventMouseLeave: function (info) {
        Array.from(document.getElementsByClassName("tooltip")).forEach(
          function (element, index, array) {
            element.remove()
          }
        );
      },
      eventResize: function() {
        normalizeCalendarEvents();
      }
    });
    calendar.render();

    // var checkboxContainer = "<div class=\"form-check\">\n" +
    //   "  <input class=\"form-check-input\" type=\"checkbox\" value=\"\" checked id=\"currentOnlyCheckbox\">\n" +
    //   "  <label class=\"form-check-label\" for=\"currentOnlyCheckbox\">\n" +
    //   "    Current Requests Only?\n" +
    //   "  </label>\n" +
    //   "</div>"
    //
    // let currentOnlyButton = $(".fc-currentOnlyButton-button")
    // let currentOnlyCheckbox = $('#currentOnlyCheckbox')
    //
    // if (typeof currentOnlyCheckbox.html() === "undefined") {
    //   currentOnlyButton.html(null)
    //   currentOnlyButton.removeClass('btn-primary')
    //   currentOnlyButton.addClass('btn-link mt-2')
    //   currentOnlyButton.html(checkboxContainer);
    // }
    //
    // $('#currentOnlyCheckbox').on('change', function () {
    //   calendar.refetchEvents()
    // })


    const updateCalendar = () => {
      const intervalId = setInterval(() => {
        resetParentsHeight();
        normalizeCalendarEvents(calendar);
      }, 50);


      setTimeout(() => {
        clearInterval(intervalId);
      }, 500);
    }

    const buttons = document.querySelectorAll("button[class*=fc-]")
    buttons.forEach((button) => {
      button.addEventListener('click', () => {
        updateCalendar();
      });
    });

    window.addEventListener('resize', () => {
      const timeSlotsTable = document.querySelector('.fc-timegrid-slots > table');
      timeSlotsTable.style.height = null;

      updateCalendar();
    });

    updateCalendar();
  }
});


const getTimeStringHourMinute = (time) => {
  return time.split(":").map(Number);
}


function resetTableHeight () {
  const timeSlotsTable = document.querySelector('.fc-timegrid-slots > table');
  timeSlotsTable.style.height = null;
}

function resetParentsHeight () {
  const trs = Array.from(document.querySelectorAll('.fc-timegrid-slots > table > tbody > tr'));

  trs.forEach((tr) => {
    tr.style.height = null;
  });

  resetTableHeight();
}

function groupEvents () {
  const eventsElements = [...document.querySelectorAll('.fc-timegrid-col-events')]
    .filter((element) => element.childElementCount)
    .map(element => Array.from(element.children))

  // all tr elements
  const trs = Array.from(document.querySelectorAll('.fc-timegrid-slots > table > tbody > tr'));

  return eventsElements.map((events) => {
    return events.reduce((group, element, index) => {
      const elementTimeStart = element.firstChild.fcSeg.start;
      const [hour, minute] = [elementTimeStart.getUTCHours(), elementTimeStart.getUTCMinutes()]

      const parent = trs.find(tr => {
        const trTime = tr.firstChild.dataset.time;
        const [slotHour, slotMinute] = getTimeStringHourMinute(trTime);

        return hour === slotHour && minute >= slotMinute && minute < slotMinute + 30;
      });

      if (parent) {
        const items = group.get(parent) || [];
        items.push(element);
        group.set(parent, items);
      }
      return group
    }, new Map())
  });
}

function setParentsHeights(eventsGroups) {
  const EVENT_MIN_HEIGHT = 24;

  // set all group of event parent height
  for (const group of eventsGroups) {
    Array.from(group.entries()).forEach(([parent, events]) => {
      const eventsHeight = events.reduce((total, item) => {
        const contentElement = item.querySelector('.fc-event-main');
        const contentElementParent = item.querySelector('.fc-event');

        contentElement.style.height = "min-content";
        contentElementParent.style.height = "min-content";
        item.style.height = "min-content";

        if (item.offsetHeight < EVENT_MIN_HEIGHT) {
          contentElement.style.height = EVENT_MIN_HEIGHT + 'px';
          contentElementParent.style.height = EVENT_MIN_HEIGHT + 'px';
          item.style.height = EVENT_MIN_HEIGHT + 'px';
        }

        return total + item.offsetHeight;
      }, 0);

      if (!parent.style.height || parent.style.height < eventsHeight) {
        parent.style.height = eventsHeight + 'px';
      }
    })
  }
}

function placeEvents (eventsGroups) {
  // place all events to the correct position in the parent
  for (const group of eventsGroups) {
    Array.from(group.entries()).forEach(([parent, events]) => {
      let currentEventsHeight = 0;
      events.forEach((item, index) => {
        item.style.inset = null;
        item.style.width = "100%";

        const parentTop = parent.offsetTop;

        item.style.top = (parentTop + currentEventsHeight)  + 'px'
        currentEventsHeight += item.offsetHeight;
      })
    })
  }
}

function normalizeCalendarEvents (calendar) {
  const eventsGroups = groupEvents();

  // fix issue with wrapping events
  const events = document.querySelectorAll(".fc-event:not(.fc-event-start)");
  events.forEach(event => event.style.display = "none")

  setParentsHeights(eventsGroups);
  placeEvents(eventsGroups);
}
