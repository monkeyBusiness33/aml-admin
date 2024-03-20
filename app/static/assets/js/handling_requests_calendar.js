"use strict";


d.addEventListener("DOMContentLoaded", function (event) {
    let calendarEl = d.getElementById('handling_requests_calendar');
    let now = new Date();

    if (calendarEl) {
        let calendar = new FullCalendar.Calendar(calendarEl, {
            timeZone: 'UTC',
            selectable: false,
            initialView: 'dayGridMonth',
            themeSystem: 'bootstrap',
            initialDate: now,
            editable: false,
            events: {
              url: handling_requests_json_url,
              extraParams: function () {

                function checkboxValue() {
                  let checkbox_el = $('#currentOnlyCheckbox')
                  return !!(typeof checkbox_el.html() === "undefined" || checkbox_el.is(':checked'));
                }

                function assignedToMeOnlyCheckboxValue() {
                  let checkbox_el = $('#requestsAssignedToMeOnlyCheckbox')
                  return !!checkbox_el.is(':checked');
                }

                return {
                  only_current: checkboxValue(),
                  only_assigned_to_me: assignedToMeOnlyCheckboxValue()
                };
              },
              success: function () {
                // setTimeout is necessary here, otherwise the event nodes cannot be found yet,
                // even though timeout time being 0 is enough. I haven't found a better way to defer this.
                setTimeout(function () {
                  let nestedTooltipsIcons = calendarEl.querySelectorAll('.nested-tooltip-icon');
                  Array.from(nestedTooltipsIcons).forEach(function (icon) {
                    icon.addEventListener('mouseenter', function (event) {
                      // Hide the tooltip of parent element
                      let eventBadge = event.target.closest('.fc-daygrid-event')
                      eventBadge.dispatchEvent(new Event('mouseleave'));

                      // Create tooltip for child element
                      let tooltip = new bootstrap.Tooltip(event.target, {
                        title: event.target.title,
                        html: true,
                        placement: 'top',
                        trigger: 'hover',
                        container: 'body'
                      });
                      tooltip.show()
                    });
                  });
                }, 0);
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
                    text: 'S&F Requests List',
                    click: function () {
                        window.location.href = handling_requests_list_url;
                    }
                },
                createHandlingRequestButton: {
                    text: 'Add Servicing & Fuelling Request',
                    click: function () {
                        window.location.href = handling_request_create_url;
                    }
                },
              currentOnlyButton: {
                text: '',
                click: function () {
                }
              },
              assignedToMeOnlyButton: {
                text: '',
                click: function () {
                }
              }
            },
            headerToolbar: {
                left: 'title',
                right: 'assignedToMeOnlyButton currentOnlyButton requestsListButton createHandlingRequestButton prev,today,next'
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
        });
        calendar.render();

        var checkboxContainer = "<div class=\"form-check\">\n" +
          "  <input class=\"form-check-input\" type=\"checkbox\" value=\"\" checked id=\"currentOnlyCheckbox\">\n" +
          "  <label class=\"form-check-label\" for=\"currentOnlyCheckbox\">\n" +
          "    Current Requests Only?\n" +
          "  </label>\n" +
          "</div>"

        let currentOnlyButton = $(".fc-currentOnlyButton-button")
        let currentOnlyCheckbox = $('#currentOnlyCheckbox')

        if (typeof currentOnlyCheckbox.html() === "undefined") {
          currentOnlyButton.html(null)
          currentOnlyButton.removeClass('btn-primary')
          currentOnlyButton.addClass('btn-link mt-2')
          currentOnlyButton.html(checkboxContainer);
        }

        $('#currentOnlyCheckbox').on('change', function () {
          calendar.refetchEvents()
        })

      var requestsAssignedToMeOnlyContainer = "<div class=\"form-check\">\n" +
          "  <input class=\"form-check-input\" type=\"checkbox\" value=\"\" id=\"requestsAssignedToMeOnlyCheckbox\">\n" +
          "  <label class=\"form-check-label\" for=\"requestsAssignedToMeOnlyCheckbox\">\n" +
          "    Requests Assigned to Me Only?\n" +
          "  </label>\n" +
          "</div>"

      let assignedToMeOnlyButton = $(".fc-assignedToMeOnlyButton-button")
      let requestsAssignedToMeOnlyCheckbox = $('#requestsAssignedToMeOnlyCheckbox')

        if (typeof requestsAssignedToMeOnlyCheckbox.html() === "undefined") {
          assignedToMeOnlyButton.html(null)
          assignedToMeOnlyButton.removeClass('btn-primary')
          assignedToMeOnlyButton.addClass('btn-link mt-2')
          if (enable_assigned_to_me_filter) {
            assignedToMeOnlyButton.html(requestsAssignedToMeOnlyContainer);
          } else {
            assignedToMeOnlyButton.remove()
          }
        }

        $('#requestsAssignedToMeOnlyCheckbox').on('change', function () {
          calendar.refetchEvents()
        })

      if (handling_request_create_url === '') {
        $('.fc-createHandlingRequestButton-button').remove()
      }

    }

});
