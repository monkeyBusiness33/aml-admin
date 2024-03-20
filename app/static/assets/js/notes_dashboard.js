$(function () {
  $(".toggle-note-read-btn").off('click').on('click', function (event) {
    event.stopPropagation();

    $.ajax({
      type: 'POST',
      url: this.dataset.url,
      dataType: 'json',
      headers: {
        'X-CSRFToken': getCSRFToken(),
      },
      success: function (resp) {
        let noteItem = event.target.closest('.single-note-item');

        if (resp.is_read) {
          noteItem.classList.remove('unread-note');
          event.target.setAttribute('data-bs-original-title', 'Mark as unread')
        } else {
          noteItem.classList.add('unread-note');
          event.target.setAttribute('data-bs-original-title', 'Mark as read')
        }
        event.target.blur();
      },
      error: function (resp) {
        console.log(resp)
      }
    });
  })
})


// Adjust the width of the last row items and height of cards in each row
function adjustCardDimensions() {
  let container = document.getElementById('note-full-container');
  let items = container?.children;

  if (!items) {
    return;
  }

  // Check if the last row is incomplete
  let containerWidth = container.offsetWidth;
  let itemFlexBasis = parseFloat(getComputedStyle(items[0]).flexBasis);
  let itemsPerRow = Math.floor(containerWidth / itemFlexBasis);
  let lastRowStartIndex = items.length - items.length % itemsPerRow;
  let targetWidth = items[0].offsetWidth;

  Array.from(items).forEach((item, i) => {
    // Adjust heights in each row


    // Adjust widths in last row
    if (i < lastRowStartIndex || lastRowStartIndex === 0) {
      item.style.maxWidth = null;
    } else {
      item.style.maxWidth = targetWidth + 'px';
    }
  });
}

// Adjust the width when the window is resized
window.addEventListener('resize', adjustCardDimensions);

// Initial adjustment on page load
adjustCardDimensions();
