from ads_bridge.models import *
from core.models import Country, Currency, Region
from aircraft.models import AircraftType, Aircraft, AircraftHistory
from django.core.exceptions import ObjectDoesNotExist
from celery import shared_task


# def sync_ads_countries():
#     ads_countries = ADS_Country.objects.using('ads').all()
#     for ads_country in ads_countries:
#         try:
#             aml_currency = Currency.objects.get(code=ads_country.currency_code)
#         except ObjectDoesNotExist as e:
#             raise ObjectDoesNotExist(
#                 f'{e} Country: {ads_country}, Currency: {ads_country.currency_code}')

#         Country.objects.update_or_create(
#             pk=ads_country.pk,
#             defaults={
#                 'code': ads_country.code,
#                 'name': ads_country.name,
#                 'continent': ads_country.continent,
#                 'currency': aml_currency,
#                 'in_eu': ads_country.in_eu,
#                 'in_schengen': ads_country.in_schengen,
#                 'in_eea': ads_country.in_eea,
#                 'in_cemac': ads_country.in_cemac,
#                 'in_ecowas': ads_country.in_ecowas,
#             },
#         )

# def sync_ads_regions():
#     ads_regions = ADS_Region.objects.using('ads').select_related('country').all()
#     for ads_region in ads_regions:
#         Region.objects.update_or_create(
#             pk=ads_region.pk,
#             defaults={
#                 'code': ads_region.code,
#                 'name': ads_region.name,
#                 'country': Country.objects.get(code=ads_region.country.code),
#             },
#         )
        
# def sync_ads_airports():
#     ads_airport_max_weight_units = ADS_AirportMaxWeightUnit.objects.using('ads').all()
#     for ads_airport_max_weight_unit in ads_airport_max_weight_units:
#         AirportMaxWeightUnit.objects.update_or_create(
#             name=ads_airport_max_weight_unit.name,
#             defaults={},
#         )
        
#     ads_airports = ADS_Airport.objects.using('ads').prefetch_related('region', 'maximum_weight_unit', 'currency_override').all()
#     for ads_airport in ads_airports:
        
#         if getattr(ads_airport, 'currency_override', None):
#             currency = Currency.objects.get(code=ads_airport.currency_override.currency_code)
#         else:
#             currency = None
            
#         if getattr(ads_airport, 'maximum_weight_unit', None):
#             maximum_weight_unit = AirportMaxWeightUnit.objects.get(
#                 name=ads_airport.maximum_weight_unit.name)
#         else:
#             maximum_weight_unit = AirportMaxWeightUnit.objects.get(pk=1)
            
#         Airport.objects.update_or_create(
#             pk=ads_airport.pk,
#             defaults={
#                 'icao_code': ads_airport.icao_code,
#                 'name': ads_airport.name,
#                 'iata_code': ads_airport.iata_code,
#                 'region_id': ads_airport.region.id,
#                 'latitude': ads_airport.latitude,
#                 'longitude': ads_airport.longitude,
#                 'maximum_weight': ads_airport.maximum_weight,
#                 'maximum_weight_unit': maximum_weight_unit,
#                 'currency_override': currency,
#                 'is_active': ads_airport.active,
#                 'has_pricing': ads_airport.has_structures,
#                 'updated_at': ads_airport.updated_at,
#             },
#         )
        
        
# def sync_ads_aircraft():
#     ads_aircraft_types = ADS_AircraftType.objects.using('ads').all()
#     for ads_aircraft_type in ads_aircraft_types:
#         AircraftType.objects.update_or_create(
#             id=ads_aircraft_type.id,
#             defaults={
#                 'designator': ads_aircraft_type.designator,
#                 'manufacturer': ads_aircraft_type.manufacturer,
#                 'model': ads_aircraft_type.model,
#                 'category': ads_aircraft_type.category,
#             },
#         )

#     ads_aircraft_list = ADS_Aircraft.objects.using('ads').all()
#     for ads_aircraft in ads_aircraft_list:
#         if ads_aircraft.ads_asn:

#             local_aircraft, created = Aircraft.objects.update_or_create(
#                 ads_asn=ads_aircraft.ads_asn,
#                 defaults={
#                     'asn': ads_aircraft.asn,
#                     'type_id': ads_aircraft.type_id,
#                     'pax_seats': ads_aircraft.pax_seats,
#                     'yom': ads_aircraft.yom,
#                     'source': ads_aircraft.source,
#                     'is_decommissioned': ads_aircraft.is_decommissioned,
#                     'created_at': ads_aircraft.created_at,
#                 },
#             )

#             ads_aircraft_history_list = ads_aircraft.aircraft_history.all()
#             for ads_aircraft_history in ads_aircraft_history_list:
#                 local_history = AircraftHistory.objects.filter(
#                     aircraft=local_aircraft, 
#                     change_effective_date=ads_aircraft_history.change_effective_date
#                 )
#                 local_homebase = Airport.objects.get(icao_code=ads_aircraft_history.homebase.icao_code)
# #                 local_operator = Oranisation.objects.filter(operator_details__ads_operator_id=ads_aircraft_history.operator_id)

#                 if local_history.exists():
#                     local_history = local_history.first()
#                     if local_history.created_at < ads_aircraft_history.created_at:
#                         local_history.registration = ads_aircraft_history.registration
# #                         local_history.operator = local_operator
#                         local_history.homebase = local_homebase
#                         local_history.source = ads_aircraft_history.source
#                         local_history.created_at = ads_aircraft_history.created_at
#                         local_history.save()
#                 else:
#                     AircraftHistory.objects.create(
#                         aircraft=local_aircraft,
#                         registration=ads_aircraft_history.registration,
#         #                 operator=local_operator,
#                         homebase=local_homebase,
#                         change_effective_date=ads_aircraft_history.change_effective_date,
#                         source=ads_aircraft_history.source,
#                         created_at=ads_aircraft_history.created_at
#                     )
#             local_aircraft_current_history = local_aircraft.aircraft_history.order_by('-change_effective_date').first()
#             local_aircraft.details=local_aircraft_current_history
#             local_aircraft.save()
            
#     # AML->ADS Aircraft Sync 
#     aml_aircraft_list = Aircraft.objects.all()
#     for aml_aircraft in aml_aircraft_list:
#         if aml_aircraft.ads_asn:
#             ads_aircraft = ADS_Aircraft.objects.using('ads').filter(ads_asn=aml_aircraft.ads_asn)
#             # Sync Aircraft
#             if not ads_aircraft.exists():
#                 ADS_Aircraft.objects.using('ads').create(
#                     ads_asn=aml_aircraft.ads_asn,
#                     asn=aml_aircraft.asn,
#                     type_id=aml_aircraft.type_id,
#                     pax_seats=aml_aircraft.pax_seats,
#                     yom=aml_aircraft.yom,
#                     source=aml_aircraft.source,
#                     is_decommissioned=aml_aircraft.is_decommissioned,
#                     created_at=aml_aircraft.created_at,
#                 )
            
#             # Sync Aircraft history
#             if ads_aircraft.exists():
#                 ads_aircraft = ads_aircraft.first()
#                 aml_aircraft_history_list = aml_aircraft.aircraft_history.all()
#                 for aml_aircraft_history in aml_aircraft_history_list:
#                     remote_history = ads_aircraft.aircraft_history.filter(
#                         aircraft=ads_aircraft, 
#                         change_effective_date=aml_aircraft_history.change_effective_date
#                     )
#                     remote_homebase = ADS_Airport.objects.using('ads').get(icao_code=aml_aircraft_history.homebase.icao_code)
#                     if remote_history.exists():
#                         remote_history = remote_history.first()
#                         if remote_history.created_at < aml_aircraft_history.created_at:
#                             remote_history.registration = aml_aircraft_history.registration
#                             remote_history.homebase = remote_homebase
#                             remote_history.source = aml_aircraft_history.source
#                             remote_history.created_at = aml_aircraft_history.created_at
#                             remote_history.save()
#                     else:
#                         ads_aircraft.aircraft_history.create(
#                             registration=aml_aircraft_history.registration,
#                             homebase=remote_homebase,
# #                             operator_id=1,
#                             change_effective_date=aml_aircraft_history.change_effective_date,
#                             source=aml_aircraft_history.source,
#                             created_at=aml_aircraft_history.created_at,
#                             created_by=1,
#                         )
#                 ads_aircraft_current_history = ads_aircraft.aircraft_history.order_by('-change_effective_date').first()
#                 ads_aircraft.details_id=ads_aircraft_current_history.id
#                 ads_aircraft.save()
