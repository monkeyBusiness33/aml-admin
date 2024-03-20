from organisation.models import GroundService


def get_supplier_service_choices():
    '''
    Get choices for the Services Provided column on Suppliers page.
    Includes all GroundService names + 'Fuel Seller' and 'Ground Handling'
    '''
    services = GroundService.objects.all().order_by('name')
    service_list = [('FS', 'Fuel Seller'), ('GH', 'Ground Handling')]
    service_list.extend(list(map(lambda x: (x.pk, x.name), services)))

    return service_list