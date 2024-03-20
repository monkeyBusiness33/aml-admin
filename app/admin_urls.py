from django.urls import path, include
from django.conf import settings
from django.contrib.auth.views import LogoutView

from chat.views import StaffChatView
from core.views.activity_log import ActivityLogAjaxView
from core.views.base import *
from core.views.comments import *
from core.views.select2 import AuthenticatedSelect2View
from handling.views.base import HandlingRequestCreatePersonAsyncCallback, \
    HandlingRequestCreateOrganisationAsyncCallback

from organisation.views.logo_motto import OrganisationLogoMottoUpdateView
from organisation.views.organisation_spf_services import OrganisationHandlerSpfServicesAjaxView, \
    OrganisationHandlerSpfServicesDetachView, HandlerManageSpfServices
from user.views._base import *
from user.views.auth import *
from user.views.people import *
from user.views.staff_user_onboarding import StaffUserOnboardingView
from user.views.index import *
from organisation.views.base import *
from organisation.views.aircraft_operators import *
from organisation.views.airport import *
from organisation.views.organisation_contact_details import *
from organisation.views.organisation_people import *
from organisation.views.organisation_document import *
from organisation.views.dao import *
from organisation.views.fuel_reseller import *
from organisation.views.organisation import *
from organisation.views.ipa import *
from organisation.views.ground_handler import *
from organisation.views.oilco import *
from organisation.views.nasdl import *
from organisation.views.service_provider import *
from organisation.views.trip_support_company import *
from organisation.views.sanctioned_organisations import *
from organisation.views.organisation_create_from_person import *
from organisation.views.organisation_payment_methods import *
from aircraft.views import *
from core.views import *
from crm.views import *
from dla_scraper.views import *
from user.views.person_documents import TravelDocumentCreateView, PersonTravelDocumentsAjaxView, \
    TravelDocumentUpdateView, TravelDocumentFileDeleteView, TravelDocumentDeleteView, PersonTravelDocumentStatusView

app_name = 'admin'
urlpatterns = [
    path('2fa-setup/', TOTPSetupView.as_view(), name='two_factor_setup'),
    path('login/', AdminLoginView.as_view(), name='login'),
    path('2fa-complete/', TotpSetupCompleteView.as_view(), name='two_factor_complete'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('select/', AuthenticatedSelect2View.as_view(), name='select2'),

    path('reset_password/<uidb64>/<token>/', StaffUserPasswordSetView.as_view(), name='staff_user_password_set'),
    path('password_set_complete/', StaffUserPasswordResetCompleteView.as_view(),
         name='staff_user_password_set_confirmation'),
    path('onboarding/', StaffUserOnboardingView.as_view(), name='staff_user_onboarding'),

    # App Includes
    path('administration/', include('administration.urls_ops')),
    path('', include('handling.urls_ops')),
    path('', include('pricing.urls_ops')),
    path('', include('supplier.urls_ops')),
    path('', include('mission.urls_ops')),
    path('', include('staff.urls_ops')),

    # Dashboard section
    # Currently Dashboard is disabled, and this should redirect to landing page appropriate for user's role
    path('dashboard/', IndexView.as_view(), name='dashboard'),

    # Aircraft
    path('aircraft/<int:pk>/edit/', AircraftEditView.as_view(), name='aircraft_edit'),

    # Organisations
    path('organisations_ajax/', OrganisationsListAjaxView.as_view(), name='organisations_ajax'),
    path('organisations/', OrganisationsListView.as_view(), name='organisations'),
    path('organisation/<int:pk>/childs/', OrganisationChildsListAjaxView.as_view(), name='organisation_childs_ajax'),
    path('organisation/<int:organisation_id>/departments_ajax/', OrganisationDepartmentsAjaxView.as_view(), name='organisation_departments_ajax'),
    path('organisation/create_for_person_position/', PersonPositionCreateOrganisationView.as_view(), name='create_for_person_position'),


    path('organisation/<int:pk>/tags/', OrganisationTagsView.as_view(), name='organisation_tags'),
    path('organisation/<int:organisation_id>/documents/', OrganisationDocumentsListAjaxView.as_view(), name='organisation_documents_ajax'),
    path('organisation/<int:organisation_id>/documents/add/', OrganisationDocumentCreateView.as_view(), name='organisation_documents_create'),
    path('organisation/document/<int:pk>/delete/', OrganisationDocumentDeleteView.as_view(), name='organisation_documents_delete'),
    path('organisations/organisation_duplicate_checker/', OrganisationsDuplicateCheckResponse.as_view(), name='organisation_duplicate_checker'),
    path('organisations/<int:organisation_id>/update_logo_motto/',
         OrganisationLogoMottoUpdateView.as_view(),
         name='organisation_logo_motto'),

    # New Organisation General Details + Create/Edit
    path('organisation/<int:pk>/', OrganisationDetailsView.as_view(), name='organisation_details'),
    path('organisations/create/', OrganisationCreateEditView.as_view(), name='organisation_create'),
    path('organisation/<int:organisation_id>/edit/', OrganisationCreateEditView.as_view(), name='organisation_edit'),
    path('organisation/<int:pk>/add_type/', OrganisationAddTypeView.as_view(), name='add_organisation_type'),

    # Organisation Additional Contact Details
    path('organisations/<int:organisation_id>/contact_details/', OrganisationContactDetailsListAjaxView.as_view(),
         name='organisation_contact_details'),
    path('organisation/<int:organisation_id>/contact_details/create/', OrganisationContactDetailsCreateView.as_view(),
         name='organisation_contact_details_create'),
    path('organisation/<int:organisation_id>/contact_details/<int:pk>/edit/', OrganisationContactDetailsEditView.as_view(),
         name='organisation_contact_details_edit'),
    path('organisation/<int:organisation_id>/contact_details/<int:pk>/delete/', OrganisationContactDetailsDeleteView.as_view(),
         name='organisation_contact_details_delete'),

    # Organisation People
    path('organisation/<int:pk>/people/', OrganisationPeopleListAjaxView.as_view(), name='organisation_people'),
    path('organisation/<int:organisation_id>/people/create/', OrganisationPersonCreateView.as_view(), name='organisation_people_create'),
    path('organisation/people/<int:organisation_people_id>/edit/', OrganisationPersonEditView.as_view(), name='organisation_people_edit'),
    path('organisation/people/<int:organisation_people_id>/detach/', OrganisationPersonDetachView.as_view(), name='organisation_people_detach'),

    # Organisation Payment Methods
    path('organisations/<int:pk>/payment_methods',
         AcceptedPaymentMethodAjaxView.as_view(),
         name='organisation_payment_methods'),
    path('organisations/<int:entity_pk>/payment_methods/add',
         PaymentMethodCreateView.as_view(),
         name='organisation_payment_methods_add'),
    path('organisations/<int:entity_pk>/payment_methods/<int:pk>/edit',
         PaymentMethodEditView.as_view(),
         name='organisation_payment_methods_edit'),
    path('organisations/<int:entity_pk>/payment_methods/<int:pk>/delete',
         AcceptedPaymentMethodDeleteView.as_view(),
         name='organisation_payment_methods_delete'),

    # Aircraft Operator
    path('organisations/aircraft_operators_ajax/', AircraftOperatorsListAjaxView.as_view(), name='aircraft_operators_ajax'),
    path('organisations/aircraft_operators/', AircraftOperatorsListView.as_view(), name='aircraft_operators'),
    path('organisations/aircraft_operators/create/', OrganisationCreateEditView.as_view(), name='aircraft_operators_create'),
    path('organisations/aircraft_operators/edit/<int:organisation_id>/', AircraftOperatorCreateEditView.as_view(), name='aircraft_operators_edit'),
    path('organisations/aircraft_operator/<int:pk>/', AircraftOperatorDetailsView.as_view(), name='aircraft_operator'),
    path('organisations/aircraft_operator/<int:operator_id>/fleet/', AircraftOperatorFleetAjaxView.as_view(), name='aircraft_operator_fleet'),
    path('organisations/aircraft_operator/<int:operator_id>/fleet/create/', AircraftOperatorFleetCreateView.as_view(), name='aircraft_operator_fleet_create'),
    path('organisations/aircraft_operator/<int:operator_id>/preferred_handlers_ajax/',
         AircraftOperatorLocationPreferredHandlerAjaxView.as_view(),
         name='aircraft_operator_preferred_handlers'),
    path('organisations/aircraft_operator/<int:operator_id>/preferred_handler_create/',
         OperatorPreferredGroundHandlerCreateView.as_view(),
         name='aircraft_operator_add_preferred_handler'),
    path('organisations/aircraft_operator/<int:pk>/preferred_handler_remove/',
         OperatorPreferredGroundHandlerDeleteView.as_view(),
         name='aircraft_operator_preferred_handler_remove'),

    # Airports
    path('organisations/airports_ajax/', AirportsListAjaxView.as_view(), name='airports_ajax'),
    path('organisations/airports/', AirportsListView.as_view(), name='airports'),
    path('organisations/airport/<int:airport_id>/ipa/', AirportIPAListAjaxView.as_view(), name='airport_ipa_ajax'),
    path('organisations/airport/<int:airport_id>/ground_handlers/', AirportGroundHandlersListAjaxView.as_view(), name='airport_ground_handlers_ajax'),
    path('organisations/airport/<int:airport_id>/airport_based_organisations/', AirportBasedOrganisationsListAjaxView.as_view(), name='airport_based_organisations_ajax'),
    path('organisations/airport/<int:pk>/', AirportDetailsView.as_view(), name='airport'),

    # DAO
    path('organisations/dao_list_ajax/', DaoListAjaxView.as_view(), name='daos_ajax'),
    path('organisations/daos/', DaoListView.as_view(), name='daos'),
    path('organisations/dao/<int:pk>/', DaoDetailsView.as_view(), name='dao'),
    path('organisations/dao/<int:dao_id>/countries/', DaoCountriesListAjaxView.as_view(), name='dao_countries_ajax'),

    # Fuel Resellers
    path('organisations/fuel_resellers_ajax/', FuelResellerListAjaxView.as_view(), name='fuel_resellers_ajax'),
    path('organisations/fuel_resellers/', FuelResellerListView.as_view(), name='fuel_resellers'),
    path('organisations/fuel_reseller/create/', OrganisationCreateEditView.as_view(), name='fuel_reseller_create'),
    path('organisations/fuel_reseller/<int:organisation_id>/edit/', FuelResellerCreateEditView.as_view(), name='fuel_reseller_edit'),
    path('organisations/fuel_reseller/<int:pk>/', FuelResellerDetailsView.as_view(), name='fuel_reseller'),
    path('organisations/fuel_reseller/<int:pk>/fuel_pricing_market_locations/',
         FuelSellerMarketPricingLocationsListAjaxView.as_view(), name='fuel_seller_market_pricing_locations_ajax'),
    path('organisations/fuel_reseller/<int:pk>/fuel_pricing_market_locations/<int:location_pk>/pricing_sublist/',
         FuelSellerMarketPricingLocationsSubListAjaxView.as_view(),
         name='fuel_seller_market_pricing_locations_sublist_ajax'),
    path('organisations/<int:pk>/fuel_agreements_ajax/',
         FuelSellerAgreementsListAjaxView.as_view(), name='fuel_seller_agreements_ajax'),
    path('organisations/fuel_reseller/<int:pk>/add_fuel_seller_tag', AddFuelSellerTagView.as_view(),
         name='add_fuel_seller_tag'),

    # Into Plane Agents (IPA)
    path('organisations/ipas_ajax/', IpaListAjaxView.as_view(), name='ipas_ajax'),
    path('organisations/ipas/', IpaListView.as_view(), name='ipas'),
    path('organisations/ipa/<int:pk>/', IpaDetailsView.as_view(), name='ipa'),
    path('organisations/ipa/<int:ipa_id>/locations_ajax/', IpaLocationsListAjaxView.as_view(), name='ipa_locations'),
    path('organisations/ipa/create/', OrganisationCreateEditView.as_view(), name='ipa_create'),
    path('organisations/ipa/<int:organisation_id>/edit/', IpaCreateEditView.as_view(), name='ipa_edit'),

    # Ground Handlers
    path('organisations/ground_handlers_ajax/', GroundHandlersListAjaxView.as_view(), name='ground_handlers_ajax'),
    path('organisations/ground_handlers/', GroundHandlersListView.as_view(), name='ground_handlers'),
    path('organisations/ground_handler/<int:pk>/', GroundHandlerDetailsView.as_view(), name='ground_handler'),
    path('organisations/ground_handler/<int:organisation_id>/edit/', GroundHandlerCreateEditView.as_view(), name='ground_handler_edit'),
    path('organisations/ground_handler/create/', OrganisationCreateEditView.as_view(), name='ground_handler_create'),
    path('organisations/ground_handler/<int:organisation_id>/fuel_types/', GroundHandlerFuelTypesUpdateView.as_view(), name='ground_handler_fuel_types'),
    path('organisations/ground_handler/<int:organisation_id>/update_ops_settings/',
         GroundHandlerOpsDetailsUpdateView.as_view(),
         name='update_ops_settings'),
    path('organisations/ground_handler/<int:organisation_id>/cancellation_bands/create/',
         HandlerCancellationBandView.as_view(),
         name='cancellation_bands_create'),
    path('organisations/ground_handler/cancellation_bands/<int:cancellation_band_id>/update/',
         HandlerCancellationBandView.as_view(),
         name='cancellation_bands_update'),
    path('organisations/ground_handler/cancellation_bands/<int:cancellation_band_id>/delete/',
         HandlerCancellationBandDeleteView.as_view(),
         name='cancellation_bands_delete'),

    # Handler SPF Services Management
    path('organisations/ground_handler/<int:organisation_id>/spf_services_ajax/',
         OrganisationHandlerSpfServicesAjaxView.as_view(),
         name='organisation_spf_services_ajax'),
    path('organisations/ground_handler/spf_service_mapping/<int:pk>/delete/',
         OrganisationHandlerSpfServicesDetachView.as_view(),
         name='organisation_spf_services_mapping_delete'),
    path('organisations/ground_handler/<int:organisation_id>/manage_spf_services/',
         HandlerManageSpfServices.as_view(),
         name='organisation_manage_spf_services'),

    # Oilco
    path('organisations/oilco_ajax/', OilcoListAjaxView.as_view(), name='oilcos_ajax'),
    path('organisations/oilcos/', OilcoListView.as_view(), name='oilcos'),
    path('organisations/oilco/<int:pk>/', OilcoDetailsView.as_view(), name='oilco'),
    path('organisations/oilco/<int:oilco_id>/fuel_types_produced/', OilcoFuelTypesListAjaxView.as_view(), name='oilco_fuel_types'),
    path('organisations/oilco/<int:oilco_id>/fuel_types_update/', OilcoFuelTypesUpdateView.as_view(), name='oilco_fuel_types_update'),
    path('organisations/oilco/create/', OrganisationCreateEditView.as_view(), name='oilco_create'),
    path('organisations/oilco/<int:organisation_id>/edit/', OilcoEditView.as_view(), name='oilco_edit'),

    # Nasdl
    path('organisations/nasdls_ajax/', NasdlListAjaxView.as_view(), name='nasdls_ajax'),
    path('organisations/nasdls/', NasdlListView.as_view(), name='nasdls'),
    path('organisations/nasdl/<int:pk>/', NasdlDetailsView.as_view(), name='nasdl'),
    path('organisations/nasdl/create/', OrganisationCreateEditView.as_view(), name='nasdl_create'),
    path('organisations/nasdl/<int:organisation_id>/edit/', NasdlCreateEditView.as_view(), name='nasdl_edit'),

    # Service Providers
    path('organisations/service_providers_ajax/', ServiceProvidersListAjaxView.as_view(), name='service_providers_ajax'),
    path('organisations/service_providers/', ServiceProvidersListView.as_view(), name='service_providers'),
    path('organisations/service_provider/<int:organisation_id>/locations_ajax/', ServiceProviderLocationsListAjaxView.as_view(), name='service_provider_locations'),
    path('organisations/service_provider/<int:pk>/', ServiceProviderDetailsView.as_view(), name='service_provider'),
    path('organisations/service_provider/create/', OrganisationCreateEditView.as_view(), name='service_provider_create'),
    path('organisations/service_provider/<int:organisation_id>/edit/', ServiceProviderCreateEditView.as_view(), name='service_provider_edit'),

    # Trip Support Companies
    path('organisations/trip_support_companies_ajax/', TripSupportCompaniesListAjaxView.as_view(), name='trip_support_companies_ajax'),
    path('organisations/trip_support_companies/', TripSupportCompaniesListView.as_view(), name='trip_support_companies'),
    path('organisations/trip_support_company/<int:pk>/', TripSupportCompanyDetailsView.as_view(), name='trip_support_company'),
    path('organisations/trip_support_company/<int:trip_support_company_id>/clients/',
         TripSupportCompanyClientsListAjaxView.as_view(), name='trip_support_company_clients'),
    path('organisations/trip_support_company/create/', OrganisationCreateEditView.as_view(), name='trip_support_company_create'),
    path('organisations/trip_support_company/<int:organisation_id>/edit/', TripSupportCompanyCreateEditView.as_view(), name='trip_support_company_edit'),

    # Sanctioned Organisations
    path('organisations/sanctioned_ajax/', SanctionedOrganisationsListAjaxView.as_view(), name='sanctioned_organisations_ajax'),
    path('organisations/sanctioned/', SanctionedOrganisationsListView.as_view(), name='sanctioned_organisations'),
    path('organisations/sanctioned/ignore/<int:pk>', SanctionedOrganisationIgnoreView.as_view(), name='sanctioned_organisation_ignore'),
    path('organisations/sanctions_exceptions/', SanctionsExceptionsListView.as_view(), name='sanctions_exceptions'),
    path('organisations/sanctions_exceptions_ajax/', SanctionsExceptionsListAjaxView.as_view(), name='sanctions_exceptions_ajax'),
    path('organisations/sanctions_exception/delete/<int:pk>/', SanctionExceptionDeleteView.as_view(), name='sanctions_exception_delete'),

    # External Users
    path('users/<int:pk>/request_password_reset/', ExternalUserPasswordResetRequestView.as_view(), name='user_request_password_reset'),
    path('users/<int:pk>/delete/', ExternalUserDeleteView.as_view(), name='user_delete'),

    # People
    path('people_ajax/', PeopleListAjaxView.as_view(), name='people_ajax'),
    path('people/', PeopleListView.as_view(), name='people'),
    path('people/person/<int:pk>/', PersonDetailsView.as_view(), name='person'),
    path('people/person/<int:pk>/tags/', PersonTagsView.as_view(), name='person_tags'),
    path('people/person/<int:person_id>/current_positions/', PersonCurrentPositionsListAjaxView.as_view(), name='person_cur_positions_ajax'),
    path('people/person/<int:person_id>/previous_positions/', PersonPreviousPositionsListAjaxView.as_view(), name='person_prev_positions_ajax'),
    path('people/person/create/', PersonCreateView.as_view(), name='person_create'),
    path('people/person/<int:person_id>/edit/', PersonCreateView.as_view(), name='person_edit'),

    # People Travel Documents
    path('people/person/<int:pk>/trvel_documents_ajax/',
         PersonTravelDocumentsAjaxView.as_view(),
         name='person_travel_documents_ajax'),

    path('people/person/<int:pk>/create/trvel_document/',
         TravelDocumentCreateView.as_view(),
         name='person_travel_document_create'),

    path('people/travel_document/<int:pk>/update/',
         TravelDocumentUpdateView.as_view(),
         name='person_travel_document_update'),

    path('people/travel_document/<int:pk>/delete/',
         TravelDocumentDeleteView.as_view(),
         name='person_travel_document_delete'),

    path('people/travel_document/file/<int:document_file_id>/delete/',
         TravelDocumentFileDeleteView.as_view(),
         name='person_travel_document_file_delete'),

    path('people/person/<int:person_id>/travel_document_status/',
         PersonTravelDocumentStatusView.as_view(),
         name='person_travel_document_status'),

    # Comments
    path('comments_ajax/<slug:entity_slug>/<int:entity_pk>/', CommentsAjaxView.as_view(), name='comments'),
    path('comments/<slug:entity_slug>/<int:entity_pk>/add/', CommentCreateView.as_view(), name='comment_add'),
    path('comments/<int:pk>/delete/', CommentDeleteView.as_view(), name='comment_delete'),
    path('comments/<int:pk>/pin/', CommentPinView.as_view(), name='comment_pin'),
    path('comments/<int:pk>/read/', CommentReadView.as_view(), name='comment_read'),

    # CRM Activity
    path('crm_activity_ajax/<slug:entity_slug>/<int:entity_pk>/', OrganisationPeopleActivitiesAjaxView.as_view(), name='crm_activity_ajax'),
    path('crm_activity/<slug:entity_slug>/<int:entity_pk>/add/', OrganisationPeopleActivityCreateView.as_view(), name='crm_activity_add'),
    path('crm_activity/<int:pk>/pin/', OrganisationPeopleActivityPinView.as_view(), name='crm_activity_pin'),

    # Activity Log
    path('activity_log_ajax/<slug:entity_slug>/<int:entity_pk>/', ActivityLogAjaxView.as_view(),
         name='activity_log_ajax'),


    # Core views
    path('ping/', DummyJsonResponse.as_view(), name='ping'),
    path('created_person_callback/<int:organisation_id>/', HandlingRequestCreatePersonAsyncCallback.as_view(), name='created_person_callback'),
    path('created_organisation_callback/', HandlingRequestCreateOrganisationAsyncCallback.as_view(), name='created_organisation_callback'),

    path('chat/', StaffChatView.as_view(), name='staff_chat'),

    # Admin index redirect (dependent on user role)
    path('', IndexView.as_view(), name='index'),

    # DLA scraper
    path('dla_contracts/', DLAContractsView.as_view(), name='dla_contracts'),
    path('dla_scraper/', DLAScraperView.as_view(), name='dla_scraper'),
    path('dla_contracts_ajax/', DLAScraperAjaxView.as_view(), name='dla_contracts_ajax'),
    path('dla_scraper_log_ajax/', DLAScraperLogAjaxView.as_view(), name='dla_scraper_log_ajax'),
    path('dla_scraper_run/', DLAScraperRunAjaxView.as_view(), name='dla_scraper_run'),
    path('dla_name_accept/', DLAReconcileNameAjaxView.as_view(), name='dla_name_accept'),
    path('dla_name_create', DLASelectOrgTypeView.as_view(), name='dla_name_create'),
    path('dla_pending_update_accept/', DLAPendingUpdateAcceptAjaxView.as_view(), name='dla_pending_update_accept'),
    path('dla_pending_update_ignore/', DLAPendingUpdateIgnoreAjaxView.as_view(), name='dla_pending_update_ignore'),
]

if settings.DEBUG:
    from core.views_debug import *
    urlpatterns += [
        path('debug/auto_spf/<int:handling_request_id>/', AutoSPFPDFView.as_view(), name='spf_auto_pdf'),
        path('debug/sign_handling_request_document/<int:document_id>/', SignHandlingRequestDocumentView.as_view(),
             name='handling_request_document_sign'),
        path('debug/handling_request_pdf/<int:handling_request_id>/',
             HandlingRequestDetailsPDFView.as_view(), name='handling_request_pdf'),
        path('debug/mission_packet_pdf/<int:mission_id>/',
             MissionPacketPDFView.as_view(), name='mission_packet_pdf_debug'),
        # path('debug/spf/<int:pk>/', SPFPDFView.as_view(), name='spf_pdf'),
    ]
