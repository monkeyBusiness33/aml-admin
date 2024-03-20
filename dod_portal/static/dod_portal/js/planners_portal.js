$(function () {
  // DoD Flight Servicing Portal Organisations selector
  $("body").on('click', '.select_dod_position', function (e) {
    e.preventDefault();
    let position_id = $(this).data("position-id")

    function getCookie(name) {
      let matches = document.cookie.match(new RegExp(
        "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"
      ))
      return matches ? decodeURIComponent(matches[1]) : undefined
    }

    $.ajax({
      type: 'POST',
      url: set_organisation_url,
      data: {
        position_id: position_id
      },
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'sessionid': getCookie('sessionid')
      },
      success: function (response) {
        location.reload();
      },
    });
  });

});
