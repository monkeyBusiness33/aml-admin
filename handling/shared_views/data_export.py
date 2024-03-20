from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.http import FileResponse

from handling.forms.data_export import MissionsExportForm
from handling.models import HandlingRequest
from handling.utils.data_export import export_handling_requests_data


class HandlingRequestDataExportMixin(BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = MissionsExportForm

    qs = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Export Servicing & Fueling Request Data',
            'icon': 'fa-file-export',
            'form_id': 'missions_export',
            'action_button_class': 'btn-success',
            'action_button_text': 'Export',
            'cancel_button_class': 'btn-gray-200',
            'alerts': [
                {
                    'text': 'File generation may take a while, please close pop-up after downloading.',
                    'class': 'alert-info',
                    'icon': 'info',
                    'position': 'top',
                }
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        only_upcoming = form.cleaned_data.get('only_upcoming')
        file = export_handling_requests_data(self.qs, start_date, end_date, only_upcoming)

        if file is None:
            form.add_error(None, 'No data to export for specified dates')
            return super().form_invalid(form)

        if not is_ajax(self.request.META):
            response = FileResponse(open(file.name, "rb"), as_attachment=True, filename='missions.csv')
            return response

        return super().form_valid(form)
