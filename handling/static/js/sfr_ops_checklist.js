$('#handling_request_ops_checklist_datatable').on('draw.dt', function (event) {
  opsChecklistDoneStatus(event);
  addCompletedEventListeners();
})

function opsChecklistDoneStatus(event) {
  let html_table = event.target;
  html_table.querySelectorAll('tr').forEach(function (row, index) {
    try {
      let completedBtn = row.querySelector('td.is_completed .toggle-item-completed-btn i');

      if (completedBtn.classList.contains("completed-item")) {
        row.classList.add('light-green-bg');
      }

    } catch (err) {
    }

  });
}

function addCompletedEventListeners() {
  $(".toggle-item-completed-btn").each(function (i, btn) {
    btn.querySelector('i').addEventListener('click', function (event) {
      $.ajax({
        type: 'POST',
        url: this.parentElement.dataset.ajaxUrl,
        dataType: 'json',
        headers: {
          'X-CSRFToken': getCSRFToken(),
        },
        success: function (resp) {
          // Redraw only the table (no need to refresh the page)
          $.fn.dataTable.tables({
            api: true
          }).filter((el) => el.id.toLowerCase().includes('ops_checklist')).draw();

          // Update the status badge
          let parser = new DOMParser();
          let oldStatusBadge = document.querySelector('.ops-checklist-status-badge');
          let newStatusBadge = parser.parseFromString(resp.status_badge_html, 'text/html').body.firstChild;

          oldStatusBadge.parentElement.replaceChild(newStatusBadge, oldStatusBadge);
        },
        error: function (resp) {
          console.log(resp)
        }
      });
    });
  })
}
