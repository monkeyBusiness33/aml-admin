from django.shortcuts import render


def error_404(request, exception):
    data = {}
    if request.user.is_anonymous:
        return render(request, 'layouts/error_404_external.html', data)
    else:
        return render(request, 'layouts/error_404_internal.html', data)


def error_500(request):
    data = {}
    return render(request, 'layouts/error_500.html', data)
