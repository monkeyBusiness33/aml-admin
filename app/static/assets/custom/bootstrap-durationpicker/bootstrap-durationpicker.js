/**
 * Bootstrap Durationpicker JQuery plugin
 *
 * Author: Oleksandr Holovatiuk
 * Created: 12/15/2023
 */

(function () {
  var _template = '<div class="duration-picker"><input class="duration-picker-placeholder form-control" autocomplete="off" readonly/><input type="hidden" name="__NAME__" /></div>';

  var _popoverContentTemplate =
    '<div class="duration-picker-popover-content">' +
    '<div class="input-wrapper"><input type="number" name="hours" step="1"/><span class="arrow-up"></span><span class="arrow-down"></span></div>' +
    '<span class="time-seperator">:</span>' +
    '<div class="input-wrapper"><input type="number" name="minutes" step="5"/><span class="arrow-up"></span><span class="arrow-down"></span></div>' +
    '</div>';

  var calcTimestamp = function (hours, minutes) {
    return (hours * 3600 + minutes * 60) * 1000;
  };

  var padZero = function (value) {
    var absValue = Math.abs(value)
    if (absValue < 10) {
      return (value < 0 ? '-' : '') + '0' + absValue;
    }

    return value;
  };

  var DurationPicker = function (element, options) {
    this.element = $(element);

    // Internal data
    this._data = {
      timestamp: 0,
      hours: 0,
      minutes: 0,
    };

    this.popoverContent = $(_popoverContentTemplate);
    this.container = $(_template.replace('__NAME__', this.element.attr('name')));
    this.placeholder = this.container.find('input.duration-picker-placeholder');
    this.inputField = this.container.find('input[type="hidden"]');

    // Render container
    this.element.replaceWith(this.container);

    // Build popover
    this.container
      .popover({
        trigger: 'manual',
        customClass: 'duration-picker-popover',
        content: this.popoverContent,
        html: true,
        offset: [0, 2],
        popperConfig: {
          placement: 'bottom-start',
        },
      })
      .on('click', function (event) {
        // Show popover when click input element
        $(this).popover('show');
      });

    var that = this;

    // Hide popover when click outside
    $(document).on('click', function (event) {
      if ($(event.target).closest('.duration-picker').length || $(event.target).closest('.duration-picker-popover').length) {
        return;
      }

      $(that.container).popover('hide');
    });

    /**
     * START event handling
     */

    // Auto select input when it get focus
    this.popoverContent.on('focus', 'input', function (event) {
      $(event.target).select();
    });

    // Auto close popover when enter key press
    this.popoverContent.on('keypress', 'input', function (event) {
      if (event.key === 'Enter') {
        $(that.container).popover('hide');
      }
    });

    // input value change
    this.popoverContent.on('change', 'input', function (event) {
      var target = event.target, name = target.name, value = target.value;
      that._data[name] = parseInt(value);

      var timestamp = calcTimestamp(that._data.hours, that._data.minutes);
      that.update(timestamp);
      that.setValue();
      that._trigger('change');
    });

    // arrow click
    this.popoverContent.on('click', '[class|="arrow"]', function (event) {
      var $input = $(event.target).siblings('input'),
        name = $input.attr('name'),
        step = $input.attr('step') || 5;
      if ($(event.target).hasClass('arrow-up')) {
        that._data[name] = parseInt($input.val()) + parseInt(step);
      } else {
        that._data[name] = parseInt($input.val()) - parseInt(step);
      }

      var timestamp = calcTimestamp(that._data.hours, that._data.minutes);
      that.update(timestamp);
      that.setValue();
      that._trigger('change');
    });

    /**
     * END event handling
     */

    this.update();
  };
  DurationPicker.prototype = {
    constructor: DurationPicker,

    _trigger: function (event, timestamp) {
      if (timestamp === undefined) {
        timestamp = this._data.timestamp;
      }
      this.container.trigger(event, timestamp);
    },
    _deriveHoursAndMinutes: function () {
      this._data.hours = Math.trunc(this._data.timestamp / 3600000);
      this._data.minutes = Math.trunc((this._data.timestamp - this._data.hours * 3600000) / 60000);
    },
    _updatePlaceholder: function () {
      this.placeholder.val(this._data.hours + ' hours and ' + this._data.minutes + ' minutes');
    },
    _updateInputs: function () {
      this.popoverContent.find('input[name="hours"]').val(padZero(this._data.hours));
      this.popoverContent.find('input[name="minutes"]').val(padZero(this._data.minutes));
    },

    update: function (value) {
      if (value === undefined) {

        value = 0;
      }

      this._data.timestamp = value;
      this._deriveHoursAndMinutes();
      this._updatePlaceholder();
      this._updateInputs();
    },
    setValue: function () {
      this.inputField.val(this._data.timestamp);
      return this;
    },
    setDuration: function (value) {
      this.update(value);
      this.setValue();
      return this;
    }
  };

  var durationPickerPlugin = function (option) {
    var args = Array.apply(null, arguments);
    args.shift();
    var internal_return;
    this.each(function () {
      var $this = $(this),
        data = $this.data('durationpicker'),
        options = typeof option === 'object' && option;

      if (!data) {
        var opts = $.extend({}, defaults, options);
        data = new DurationPicker(this, opts);
        data.container.data('durationpicker', data);
      }
      if (typeof option === 'string' && typeof data[option] === 'function') {
        internal_return = data[option].apply(data, args);
      }
    });

    if (internal_return === undefined) {
      return this;
    }

    return internal_return;
  };
  $.fn.durationpicker = durationPickerPlugin;

  var defaults = $.fn.durationpicker.defaults = {};
})();

$(function () {
  $('.duration-picker').durationpicker();
});
