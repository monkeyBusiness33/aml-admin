function fill_notification_list2(data) {
  var menus = document.getElementsByClassName(notify_menu_class);
  if (menus) {
    var messages = data.unread_list.map(function (item) {
      var message = "";
      if (typeof item.actor !== 'undefined') {
        message = item.actor;
      }
      if (typeof item.verb !== 'undefined') {
        message = message + " " + item.verb;
      }
      if (typeof item.target !== 'undefined') {
        target = item.target;
      } else {
        target = item.actor;
      }
      if (typeof item.timestamp !== 'undefined') {
        message = message + " " + item.timestamp;
      }
      var description = item.description ?? ''

      message_html = '<li id="' + item.slug + '" class="list-group-item list-group-item-action border-bottom"> \
            <div class="row align-items-center"> \
                <div class="col ps-0 ms-2"> \
                    <div class="d-flex justify-content-between align-items-center"> \
                        <div> \
                        <h4 class="h6 mb-0 text-small">' + item.verb + '</h4> \
                        </div> \
                        <div class="text-end"> \
                        <small>' + moment(item.timestamp).fromNow() + '</small> \
                        </div> \
                    </div> \
                    <p class="font-small mt-1 mb-0 ttttttt">' + description + '</p> \
                </div> \
            </div>'
      '</li>';
      return message_html;
    }).join('')

    for (var i = 0; i < menus.length; i++) {
      menus[i].innerHTML = messages;
    }
  }
}

function fill_notification_badge2(data) {
  var badges = document.getElementsByClassName("notification-bell dropdown-toggle");
  if (badges) {
    if (data.unread_count > 0) {
      for (var i = 0; i < badges.length; i++) {
        badges[i].classList.add("unread");
      }
    }
  }
}

$(function () {
  // Mark as read clicked notification
  $("body").on('click', '.dropdown-menu li', function (e) {
    $.ajax({
      url: '/inbox/notifications/mark-as-read/' + this.id + '/',
      type: 'get',
    });
  });

  // Mark as read all notifictions button
  $('.notifications-mark-as-read').on('click', function () {
    $.ajax({
      url: '/inbox/notifications/mark-all-as-read/',
      type: 'get',
    });
  });

});

