from datetime import datetime

from django.db import models
from django.urls import reverse_lazy

from core.utils.datatables_functions import get_datatable_badge


class PricingBacklogEntry(models.Model):
    """
    Dummy abstract model to satisfy the requirement for model field in FuelPricingBacklogAjaxView
    Also serves as an abstract base class to hold backlog-related methods for all relevant classes,
    """
    expiry_date = None
    locations_str = None
    type = None
    priority = None
    url_pk = None

    TYPES = {
        'S': 'Supplier Agreement',
        'I': 'Fuel Index Pricing',
        'M': 'Market Pricing',
    }

    class Meta:
        abstract = True

    @property
    def type_str(self):
        return self.TYPES[self.type]

    @property
    def backlog_url(self):
        if self.type == 'M':
            return reverse_lazy('admin:fuel_pricing_market_document_details', kwargs={'pk': self.url_pk})
        elif self.type == 'I':
            return reverse_lazy('admin:fuel_index_details', kwargs={'pk': self.url_pk})
        elif self.type == 'S':
            return reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.url_pk})

    @property
    def expiry_badge(self):
        badge_text = self.expiry_date.strftime("%Y-%m-%d") \
            if self.expiry_date else 'Until Further Notice'

        if not self.expiry_date or self.expiry_date > datetime.today().date():
            badge_color_cls = 'green_backlog_badge'
        elif self.expiry_date == datetime.today().date():
            badge_color_cls = 'yellow_backlog_badge'
        else:
            badge_color_cls = 'red_backlog_badge'

        badge_str = get_datatable_badge(
            badge_text=badge_text,
            badge_class=f'{badge_color_cls} datatable-badge-normal badge-multiline badge-250 nowrap',
            tooltip_enable_html=True
        )

        return badge_str

    @property
    def location_badges_str(self):
        badge_str = ''
        locations = [s for s in self.locations_str.split(', ') if s != ' / ']

        if not locations:
            return '--'

        for location in locations:
            badge_str += get_datatable_badge(
                badge_text=location,
                badge_class='bg-info datatable-badge-normal badge-multiline badge-250',
                tooltip_enable_html=True
            )

        return f'<div class="d-flex flex-wrap">{badge_str}</div>'

    @property
    def priority_badge(self):
        if self.priority == 0:
            badge_text = 'Urgent'
            badge_color_cls = 'purple_backlog_badge'
        elif self.priority == 1:
            badge_text = 'High'
            badge_color_cls = 'red_backlog_badge'
        elif self.priority == 2:
            badge_text = 'Medium'
            badge_color_cls = 'yellow_backlog_badge'
        else:
            badge_text = 'Low'
            badge_color_cls = 'green_backlog_badge'

        badge_str = get_datatable_badge(
            badge_text=badge_text,
            badge_class=f'{badge_color_cls} datatable-badge-normal badge-multiline badge-250 nowrap',
            tooltip_enable_html=True
        )

        return badge_str
