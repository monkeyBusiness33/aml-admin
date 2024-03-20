from core.models.tag import Tag


def update_organisation_default_tags(organisation):
    is_customer_tag_name = 'Customer'
    is_fuel_seller_tag_name = 'Fuel Seller'
    is_service_supplier_tag_name = 'Service Supplier'
    is_competitor_tag_name = 'Competitor'
    
    organisation_restricted = getattr(
        organisation, 'organisation_restricted', None)
    if organisation_restricted:
    
        if organisation.organisation_restricted.is_customer:
            tag, created = Tag.objects.get_or_create(
                name=is_customer_tag_name, is_system=True)
            organisation.tags.add(tag)
        else:
            tag, created = Tag.objects.get_or_create(
                name=is_customer_tag_name, is_system=True)
            organisation.tags.remove(tag)
        
        if organisation.organisation_restricted.is_fuel_seller:
            tag, created = Tag.objects.get_or_create(
                name=is_fuel_seller_tag_name, is_system=True)
            organisation.tags.add(tag)
        else:
            tag, created = Tag.objects.get_or_create(
                name=is_fuel_seller_tag_name, is_system=True)
            organisation.tags.remove(tag)
            
        if organisation.organisation_restricted.is_service_supplier:
            tag, created = Tag.objects.get_or_create(
                name=is_service_supplier_tag_name, is_system=True)
            organisation.tags.add(tag)
        else:
            tag, created = Tag.objects.get_or_create(
                name=is_service_supplier_tag_name, is_system=True)
            organisation.tags.remove(tag)
        
        if organisation.organisation_restricted.is_competitor:
            tag, created = Tag.objects.get_or_create(
                name=is_competitor_tag_name, is_system=True)
            organisation.tags.add(tag)
        else:
            tag, created = Tag.objects.get_or_create(
                name=is_competitor_tag_name, is_system=True)
            organisation.tags.remove(tag)
    
    # Fuel Reseller / Fuel Agent organisation tags
    fuel_reseller_tag_name = 'Fuel Reseller'
    fuel_agent_tag_name = 'Fuel Agent'
    
    organisation_details = getattr(organisation, 'details', None)
    if organisation_details:
        if organisation.details.type.id == 2:
            tag, created = Tag.objects.get_or_create(
                name=fuel_reseller_tag_name, is_system=True)
            organisation.tags.add(tag)
        else:
            tag, created = Tag.objects.get_or_create(
                name=fuel_reseller_tag_name, is_system=True)
            organisation.tags.remove(tag)
            
        if organisation.details.type.id == 13:
            tag, created = Tag.objects.get_or_create(
                name=fuel_agent_tag_name, is_system=True)
            organisation.tags.add(tag)
        else:
            tag, created = Tag.objects.get_or_create(
                name=fuel_agent_tag_name, is_system=True)
            organisation.tags.remove(tag)
