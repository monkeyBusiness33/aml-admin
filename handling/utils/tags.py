from core.models.tag import Tag


def update_handling_service_default_tags(handling_service):
    is_dla_tag_name = 'DLA Service'
    
    if handling_service.is_dla == True:
        tag, created = Tag.objects.get_or_create(name=is_dla_tag_name)
        handling_service.tags.add(tag)
    else:
        tag, created = Tag.objects.get_or_create(name=is_dla_tag_name)
        handling_service.tags.remove(tag)
    
        