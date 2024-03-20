from user.models import TravelDocument


def process_travel_documents_validity():
    """
    This function check all travel documents validity dates and update it's 'is_current' status
    :return:
    """
    travel_documents = TravelDocument.objects.filter(
        is_current=True,
    ).all()
    
    for document in travel_documents:
        if not document.is_valid:
            document.is_current = False
            document.save()
