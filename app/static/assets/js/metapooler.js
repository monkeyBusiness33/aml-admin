// Pooling function to the meta information like Requests awaiting review and etc

const MetaPooler = (function () {

  const RECONNECT_INTERVAL = 5000;
  const POOLING_INTERVAL = 1500;

  const unread_messages_badge = $('#chat_unread_messages_badge');
  const chat_unread_messages_counter = $('.chat_unread_messages_counter');

  const chat_unread_messages_counter_raw = $('.chat_unread_messages_counter_raw');

  const srf_counter_badge_new = $('#srf_counter_badge_new');
  const handling_requests_count = $('.handling_requests_count');

  const unread_notes_counter_badge = $('#unread_notes_counter_badge');
  const unread_notes_count = $('#unread_notes_count');

  const current_date_div = $('#current_system_time');

  const spf_to_reconcile_counter = $('.spf_to_reconcile_counter')

  function update_chat_unread_messages_counter(unread_messages) {
    const existing_value = chat_unread_messages_counter.html()

    // Stop executing if no badge on the page (no permission)
    if (typeof existing_value == "undefined") {
      return
    }

    if (unread_messages > 0) {
      const text = 'DoD Comms: ' + unread_messages

      if (text !== existing_value.toString()) {
        chat_unread_messages_counter_raw.html(unread_messages)
        chat_unread_messages_counter.html(text)
        unread_messages_badge.removeClass('bg-gray-400 text-white')
        unread_messages_badge.addClass('bg-secondary text-primary')
      }
    } else if (unread_messages === 0) {
      if (chat_unread_messages_counter_raw.html()) {
        chat_unread_messages_counter_raw.html(null)
      }

      if (chat_unread_messages_counter.html() !== 'DoD Comms') {
        chat_unread_messages_counter.html('DoD Comms')
        unread_messages_badge.removeClass('bg-secondary text-primary')
        unread_messages_badge.addClass('bg-gray-400 text-white')
      }
    }
  }


  function update_spf_to_reconcile_counter(value) {
    const existing_value = spf_to_reconcile_counter.html()

    // Stop executing if no badge on the page (no permission)
    if (typeof existing_value == "undefined") {
      return
    }

    if (value > 0) {
      if (value !== existing_value.toString()) {
        spf_to_reconcile_counter.html(value)
      }
    } else if (value === 0) {
      if (spf_to_reconcile_counter.html()) {
        spf_to_reconcile_counter.html(null)
      }

    }
  }


  function update_srf_counter_counter(handling_requests) {
    const text = handling_requests ? 'S&F Requests: ' + handling_requests : 'No New S&F Requests';

    if (text === handling_requests_count.text()) {
      return;
    }

    handling_requests_count.text(text)
    if (handling_requests) {
      srf_counter_badge_new.addClass('bg-danger')
      srf_counter_badge_new.removeClass('bg-gray-400')
    } else {
      srf_counter_badge_new.removeClass('bg-danger')
      srf_counter_badge_new.addClass('bg-gray-400')
    }
  }

  function update_unread_notes_counter(unread_notes) {
    const text = unread_notes ? 'Unread Notes: ' + unread_notes : 'No Unread Notes';

    if (text === unread_notes_count.text()) {
      return;
    }

    unread_notes_count.text(text)

    if (unread_notes) {
      unread_notes_counter_badge.addClass('bg-warning')
      unread_notes_counter_badge.removeClass('bg-gray-400')
    } else {
      unread_notes_counter_badge.removeClass('bg-warning')
      unread_notes_counter_badge.addClass('bg-gray-400')
    }
  }

  function update_current_time(current_time) {
    if (current_date_div.text() === current_time) {
      return;
    }

    current_date_div.text(current_time)
  }

  function websocket_connect() {
    const ws_protocol = window.location.protocol === 'http:' ? 'ws://' : 'wss://';

    const socket = new WebSocket(ws_protocol + window.location.host + "/chat/ws/notifications/");

    socket.onopen = function () {
      setInterval(websocket_pool, POOLING_INTERVAL);
    }

    socket.onmessage = function (event) {
      onMessage(event)
    }

    socket.onclose = function (event) {
      socket.close()

      // Do not reconnect after auth fail
      if (event.code !== 4003) {
        setTimeout(function () {
          websocket_connect();
        }, RECONNECT_INTERVAL);
      }

    }

    function onMessage(event) {
      const message = JSON.parse(event.data)

      if (message.type === 'notifications_data') {
        const unread_messages = message.unread_messages;
        const handling_requests = message.handling_requests;
        const spf_to_reconcile = message.spf_to_reconcile;
        const unread_notes = message.unread_notes;
        const current_time = message.current_time;

        unread_messages !== undefined && update_chat_unread_messages_counter(unread_messages);
        handling_requests !== undefined && update_srf_counter_counter(handling_requests);
        spf_to_reconcile !== undefined && update_spf_to_reconcile_counter(spf_to_reconcile);
        unread_notes !== undefined && update_unread_notes_counter(unread_notes);
        current_time !== undefined && update_current_time(current_time);
      }
    }

    function websocket_pool() {
      if (!document.hidden) {
        const jsonData = JSON.stringify({type: 'get_notifications'});
        if (socket.readyState === 1) {
          socket.send(jsonData)
        }
      }
    }
  }

  return {
    init: function () {
      websocket_connect();
    }
  }
})()

$(document).ready(function () {
  MetaPooler.init()
})
