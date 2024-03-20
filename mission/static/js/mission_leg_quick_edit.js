var MissionLegQuickEdit = (function () {

  var initDurationpicker = function () {
    $('.duration-picker').durationpicker();
  };

  var syncValues = function () {
    var $departure_datetime = $('input[name="departure_datetime"]');
    var $arrival_datetime = $('input[name="arrival_datetime"]');
    var $time_en_route = $('input[name="time_en_route"]');

    var sync_time_en_route = function () {
      var departure_datetime_val = $departure_datetime.val();
      var arrival_datetime_val = $arrival_datetime.val();

      if (!departure_datetime_val || !arrival_datetime_val) {
        return;
      }

      var departureDate = new Date(departure_datetime_val);
      var arrivalDate = new Date(arrival_datetime_val);
      var duration = arrivalDate.getTime() - departureDate.getTime();

      $time_en_route.parent().durationpicker('setDuration', duration);
    };

    var sync_arrival_datetime = function () {
      var departure_datetime_val = $departure_datetime.val();
      var time_en_route_val = $time_en_route.val();

      if (!departure_datetime_val || !time_en_route_val) {
        return;
      }

      var departureDate = new Date(departure_datetime_val);
      var arrivalDate = new Date(departureDate.getTime() + parseInt(time_en_route_val));

      var fp = $arrival_datetime.parent()[0]._flatpickr;
      fp.setDate(arrivalDate);
    }

    $departure_datetime.parent().on('change', sync_arrival_datetime);
    $arrival_datetime.parent().on('change', sync_time_en_route);
    $time_en_route.parent().on('change', sync_arrival_datetime);

    sync_time_en_route();
  }

  return {
    init: function () {
      initDurationpicker();
      syncValues();
    }
  }
})();

$(function () {
  MissionLegQuickEdit.init();
});
