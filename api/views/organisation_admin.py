from django.db.models import Q
from rest_framework import generics, filters
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from api.serializers.organisation import OrganisationSerializer, OrganisationPeopleSerializer
from organisation.models import Organisation, OrganisationPeople


class OrganisationsListView(generics.ListAPIView):
    """
    | DoD Organisations list for Staff Users
    | URI: /admin/organisations/
    """
    renderer_classes = [JSONRenderer]
    serializer_class = OrganisationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter]

    def get_queryset(self):
        search_term = self.request.query_params.get('search')
        search_q = Q()
        if search_term:
            search_q = Q(
                Q(details__registered_name__icontains=search_term) |
                Q(details__trading_name__icontains=search_term)
            )

        qs = Organisation.objects.aircraft_operator_military()
        qs = qs.filter(search_q)
        return qs


class OrganisationPeopleListView(generics.ListAPIView):
    """
    | Organisation people list for Staff Users
    | URI: /admin/organisations/<organisation_id>/people/
    """
    renderer_classes = [JSONRenderer]
    serializer_class = OrganisationPeopleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        qs = OrganisationPeople.objects.filter(
            organisation_id=self.kwargs['pk'],
            role__code_name__in=['FCR', 'OPP', ],
        ).select_related(
            'person', 'role',
        ).prefetch_related(
            'person__details',
        )
        return qs
