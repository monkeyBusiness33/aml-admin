from django.http import JsonResponse
from django_select2.views import AutoResponseView


class HandlingServiceSelect2Mixin(AutoResponseView):

    widget = None
    term = ''
    object_list = []

    def get(self, request, *args, **kwargs):
        self.widget = self.get_widget_or_404()
        self.term = kwargs.get("term", request.GET.get("term", ""))
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return JsonResponse(
            {
                "results": [
                    {"text": self.widget.label_from_instance(obj),
                     "id": obj.pk,
                     "is_allowed_free_text": obj.is_allowed_free_text,
                     "is_allowed_quantity_selection": obj.is_allowed_quantity_selection,
                     "quantity_selection_uom": obj.quantity_selection_uom.description_plural if
                     obj.quantity_selection_uom else None,
                     }
                    for obj in context["object_list"]
                ],
                "more": context["page_obj"].has_next(),
            }
        )
