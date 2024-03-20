DJANGO_FLATPICKR = {
    # Name of the theme to use
    # More themes: https://flatpickr.js.org/themes/
    "theme_name": "confetti",
    #
    # Complete URL of theme CSS file
    # theme_name is ignored if theme_url is provided
    # "theme_url": "https://..",
    #
    # Global HTML attributes for flatpickr <input> element
    # "attrs": {
    #     "class": "my-custom-class",
    #     "placeholder": "Select Date..",
    # },
    #
    # Global options for flatpickr
    # More options: https://flatpickr.js.org/options/
    # Some options are managed by this package e.g mode, dateFormat, altInput
    "options": {
        # "locale": "bn",             # locale option can be set here only
        "altFormat": "Y-m-d H:i",   # specify date format on the front-end
        "time_24hr": True,
        "allowInput": True,
    },
    # You can set date and event hook options using JavaScript, usage in README.
    #
    # HTML template to render the flatpickr input
    # Example: https://github.com/monim67/django-flatpickr/blob/2.0.0/dev/myapp/templates/myapp/custom-flatpickr-input.html
    # "template_name": "your-app/custom-flatpickr-input.html",
    #
    # Specify CDN roots. Choose where from static JS/CSS are served.
    # Can be set to localhost (offline setup) or any other preferred CDN.
    # The default values are:
    #    "flatpickr_cdn_url": "https://cdn.jsdelivr.net/npm/flatpickr@4.6.13/dist/",
    #    "app_static_url": "https://cdn.jsdelivr.net/gh/monim67/django-flatpickr@2.0.0/src/django_flatpickr/static/django_flatpickr/",
    #
    # Advanced:
    # If you want to serve static files yourself without CDN (from staticfiles) and
    # you know how to serve django static files on production server (DEBUG=False)
    # Then download and extract https://registry.npmjs.org/flatpickr/-/flatpickr-4.6.13.tgz
    # Copy the dist directory (package/dist) to any of your static directory and rename it to flatpickr
    # and use following options
       "flatpickr_cdn_url": "assets/vendor/flatpickr-4.6.13/",
       "app_static_url": "assets/vendor/django-flatpickr/",
}
