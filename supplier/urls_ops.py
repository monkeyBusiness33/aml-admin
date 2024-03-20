from django.urls import path
from supplier.views import *

urlpatterns = [
    path('suppliers/', SuppliersListView.as_view(), name='suppliers'),
    path('suppliers_ajax/', SuppliersListAjaxView.as_view(), name='suppliers_ajax'),
]
