// NASDL Pages Google Map functionality

$(document).ready(function () {

    var map;
    var default_map_coordinatess = [2.290569, 48.895651];

    function initialize_google_map(coordinates) {
        var myLatlng = new google.maps.LatLng(coordinates[1], coordinates[0]);
        map = new google.maps.Map(
            document.getElementById("nasdl_map"), {
                center: myLatlng,
                zoom: 13,
                mapTypeId: google.maps.MapTypeId.ROADMAP,
                overviewMapControl: false,
                streetViewControl: false,
                mapTypeControl: false,
            });
        var marker = new google.maps.Marker({
            position: myLatlng,
            map: map
        })
        return map;
    }

    function setMapFromFormLatLonFields() {
        var latitude = $("#id_nasdl_details_form_pre-latitude").val()
        var longitude = $("#id_nasdl_details_form_pre-longitude").val()
        initialize_google_map([longitude, latitude])
    }

    function w3w_field_update_state() {
        var w3w_value = $("#id_nasdl_details_form_pre-what3words_code").val()
        if (w3w_value == '') {
            if ($("#id_nasdl_details_form_pre-longitude").val() !== '' || $("#id_nasdl_details_form_pre-latitude").val() !== '') {
                $("#id_nasdl_details_form_pre-what3words_code").prop("disabled", true)
                $("#id_nasdl_details_form_pre-use_address").val(false).prop("disabled", true);
            } else {
                $("#id_nasdl_details_form_pre-what3words_code").prop("disabled", false)
                $("#id_nasdl_details_form_pre-use_address").val(false).prop("disabled", false);
            }
        }
    }

    // Lat/Lng Fields actions
    $("#id_nasdl_details_form_pre-latitude").change(function () { // 1st way
        w3w_field_update_state()
        setMapFromFormLatLonFields()
    });

    $("#id_nasdl_details_form_pre-longitude").change(function () { // 1st way
        w3w_field_update_state()
        setMapFromFormLatLonFields()
    });

    // W3W response actions
    if ($('what3words-autosuggest').length) {
        document.querySelector('what3words-autosuggest')
            .addEventListener("coordinates_changed", (value) => {
                $("#id_nasdl_details_form_pre-latitude").val(value.detail.coordinates.lat).prop("readonly", true).change();
                $("#id_nasdl_details_form_pre-longitude").val(value.detail.coordinates.lng).prop("readonly", true).change();
                $("#id_nasdl_details_form_pre-use_address").val(false).prop("disabled", true);

            });
    };


    // Enable all fields on W3W code cleaning
    $("#id_nasdl_details_form_pre-what3words_code").change(function () {
        if ($(this).val() == '') {
            $("#id_nasdl_details_form_pre-latitude").val(null).prop("readonly", false).change();
            $("#id_nasdl_details_form_pre-longitude").val(null).prop("readonly", false).change();
            $("#id_nasdl_details_form_pre-use_address").val(false).prop("disabled", false);
        }
    });

    function setMapViaGeocoder(address) {
        var geocoder;
        geocoder = new google.maps.Geocoder();
        geocoder.geocode({
            'address': address
        }, function (results, status) {
            if (status == google.maps.GeocoderStatus.OK) {
                initialize_google_map([results[0].geometry.location.lng(), results[0].geometry.location.lat()])
                // map.setCenter(results[0].geometry.location);
                // var marker = new google.maps.Marker({
                //     map: map,
                //     position: results[0].geometry.location,
                //     icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                // });
            } else {
                console.log('Geocode was not successful for the following reason: ' + status);
            }
        });
    }

    function setMapFromAddress(form) {
        var formPrefix = $(form).attr('data-address-form-pre')
        var use_address_checkbox = $("#id_nasdl_details_form_pre-use_address").is(':checked')
        var country_html_val = $('#id_organisation_address_formset_pre-0-country').val()
        var address_line_1 = $('#id_' + formPrefix + '-line_1').val()
        var address_line_2 = $('#id_' + formPrefix + '-line_2').val()
        var address_line_3 = $('#id_' + formPrefix + '-line_3').val()
        var address_state = $('#id_' + formPrefix + '-state').val()
        var address_city = $('#id_' + formPrefix + '-town_city').val()
        var address_zipcode = $('#id_' + formPrefix + '-post_zip_code').val()

        if (use_address_checkbox && country_html_val && address_line_1) {
            var address_country = $('#id_' + formPrefix + '-country').select2('data')[0].text
            var search_address = address_country + ', ' + address_state + ', ' + address_city + ', ' + address_line_1 + ', ' + address_line_2 + ', ' + address_line_3 + ', ' + address_zipcode
            setMapViaGeocoder(search_address)
        };
    }

    $('.address_form:not(.to_delete,.d-none):first').change(function () {
        setMapFromAddress(this)
    });

    // Disable and clear other fields on "Use Address" ckeck
    $("#id_nasdl_details_form_pre-use_address").change(function () { // 1st way
        if ($(this).is(':checked')) {
            $("#id_nasdl_details_form_pre-what3words_code").prop("disabled", true).prop('required', false);
            $("#id_nasdl_details_form_pre-latitude").val(null).prop("disabled", true).prop('required', false);
            $("#id_nasdl_details_form_pre-longitude").val(null).prop("disabled", true).prop('required', false);
        } else {
            $("#id_nasdl_details_form_pre-what3words_code").prop("disabled", false).prop('required', true);
            $("#id_nasdl_details_form_pre-latitude").val(null).prop("disabled", false).prop('required', true);
            $("#id_nasdl_details_form_pre-longitude").val(null).prop("disabled", false).prop('required', true);
        }

        var form = $('.address_form:not(.to_delete,.d-none):first')
        setMapFromAddress(form)
    });

    $(document).ready(function () {

        if ($("#nasdl_details_form").length) {
            var use_address_checkbox = $("#id_nasdl_details_form_pre-use_address").is(':checked')
            var form = $('.address_form:not(.to_delete,.d-none):first')
            var latitude = $("#id_nasdl_details_form_pre-latitude").val()
            var longitude = $("#id_nasdl_details_form_pre-longitude").val()
            if (use_address_checkbox) {
                setMapFromAddress(form)
            } else {
                if (latitude !== '' && longitude !== '') {
                    setMapFromFormLatLonFields()
                }
            }
        };

        if ($("#nasdl-details-container").length) {
            if (nasdl_details_use_address_for_location == 'true'){
                var search_address = nasdl_details_address_country + ', ' + nasdl_details_address_state + ', ' + nasdl_details_address_city + ', ' + nasdl_details_address_line_1 + ', ' + nasdl_details_address_line_2 + ', ' + nasdl_details_address_line_3 + ', ' + nasdl_details_address_post_zip_code
                setMapViaGeocoder(search_address)
            }
            else if (nasdl_details_latitude !== '' && nasdl_details_longitude !== '') {
                initialize_google_map([nasdl_details_longitude, nasdl_details_latitude])
            }
        };

    });

    $(window).on('click change load', function () {
        if ($("#nasdl_details_form").length) {
            var use_address_checkbox = $("#id_nasdl_details_form_pre-use_address").is(':checked')
            var form = $('.address_form:not(.to_delete,.d-none):first')
            var formPrefix = $(form).attr('data-address-form-pre')

            if (use_address_checkbox) {
                $(form).addClass('border border-danger')
                var delete_btn = $(form).find('.del_organisation_address_btn')
                $(delete_btn).prop('disabled', true);

                $('#id_' + formPrefix + '-is_physical_address').prop('checked', true).prop("readonly", true);
                $('#id_' + formPrefix + '-line_1').prop('required', true);
                $('#id_' + formPrefix + '-town_city').prop('required', true);
                $('#id_' + formPrefix + '-country').prop('required', true);
                $('#id_' + formPrefix + '-post_zip_code').prop('required', true);

                $("#id_nasdl_details_form_pre-latitude").prop("required", false).prop("readonly", true);
                $("#id_nasdl_details_form_pre-longitude").prop("required", false).prop("readonly", true);
                $("#id_nasdl_details_form_pre-what3words_code").prop("required", false).prop("readonly", true);
            } else {
                $(form).removeClass('border border-danger')
                var delete_btn = $(form).find('.del_organisation_address_btn')
                $(delete_btn).prop('disabled', false);

                $('#id_' + formPrefix + '-is_physical_address').prop("readonly", false);
                $('#id_' + formPrefix + '-line_1').prop('required', false);
                $('#id_' + formPrefix + '-town_city').prop('required', false);
                $('#id_' + formPrefix + '-country').prop('required', false);
                $('#id_' + formPrefix + '-post_zip_code').prop('required', false);


                var w3w_value = $("#id_nasdl_details_form_pre-what3words_code").val()
                if (w3w_value == '') {
                    $("#id_nasdl_details_form_pre-latitude").prop("required", true).prop("readonly", false);
                    $("#id_nasdl_details_form_pre-longitude").prop("required", true).prop("readonly", false);
                }
                $("#id_nasdl_details_form_pre-what3words_code").prop("required", true).prop("readonly", false);
            }
        };
    });

});
