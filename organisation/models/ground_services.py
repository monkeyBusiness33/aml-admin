from django.db import models
from django.utils.translation import gettext_lazy as _


class OrganisationServiceProviderLocation(models.Model):
    organisation = models.ForeignKey("organisation.Organisation", 
                                     verbose_name=_("Organisation"),
                                     related_name='service_provider_locations',
                                     on_delete=models.CASCADE)
    delivery_location = models.ForeignKey("organisation.Organisation", 
                                          limit_choices_to={'details__type_id__in': [8, 1002]},
                                          verbose_name=_("Delivery Location"),
                                          related_name='service_provider_locations_here',
                                          on_delete=models.CASCADE)
    is_fbo = models.BooleanField(_("FBO?"), default=False)
    ground_services = models.ManyToManyField("organisation.GroundService", 
                                             through='organisation.OrganisationServiceProviderLocationService',
                                             related_name='locations', blank=True)
    
    class Meta:
        db_table = 'organisations_service_providers_locations'

    def __str__(self):
        return f'{self.pk}'


class OrganisationServiceProviderLocationService(models.Model):
    location = models.ForeignKey("organisation.OrganisationServiceProviderLocation",
                                     verbose_name=_("Location"),
                                     related_name='services',
                                     on_delete=models.CASCADE)
    service = models.ForeignKey("organisation.GroundService",
                                verbose_name=_("Service"),
                                on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_service_providers_locations_services'

    def __str__(self):
        return f'{self.service}'


class GroundService(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    is_de_icing = models.BooleanField(_("De-icing?"), default=False)
    
    de_icing_type = models.ForeignKey("organisation.GroundServiceDeIcingType",
                                 verbose_name=_("De-icing Type"),
                                 related_name='de_icing_services',
                                 null=True, blank=True,
                                 on_delete=models.CASCADE)
    is_anti_icing = models.BooleanField(_("Anti-icing?"), default=False)
    anti_icing_type = models.ForeignKey("organisation.GroundServiceDeIcingType",
                                        verbose_name=_("Anti-icing Type"),
                                        related_name='anti_icing_services',
                                        null=True, blank=True,
                                        on_delete=models.CASCADE)
    is_maintenance = models.BooleanField(_("Maintenance?"), default=False)
    is_cleaning = models.BooleanField(_("Cleaning?"), default=False)
    is_equipment_rental = models.BooleanField(_("Equipment Rental?"), default=False)
    is_catering = models.BooleanField(_("Catering?"), default=False)
    is_transport = models.BooleanField(_("Transport?"), default=False)

    class Meta:
        db_table = 'aviation_ground_services'

    def __str__(self):
        return f'{self.name}'


class GroundServiceDeIcingType(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    is_de_icing = models.BooleanField(_("De-icing?"), default=False)
    is_anti_icing = models.BooleanField(_("Anti-icing?"), default=False)
    is_mechanical = models.BooleanField(_("Mechanical?"), default=False)
    is_thermal = models.BooleanField(_("Thermal?"), default=False)
    is_liquid = models.BooleanField(_("Liquid?"), default=False)
    fluid_ratio = models.IntegerField(_("Fluid Ratio"), null=True, blank=True)
    water_ratio = models.IntegerField(_("Water Ratio"), null=True, blank=True)
    colour = models.CharField(_("Colour"), max_length=50)
    holdover_time_minimum = models.TimeField(_("Holdover Time Min"), auto_now=False, auto_now_add=False)
    holdover_time_maximum = models.TimeField(_("Holdover Time Max"), auto_now=False, auto_now_add=False)
    minimum_rotation_speed_kts = models.IntegerField(_("Min Rotation Speed KTS"), null=True, blank=True)
    
    class Meta:
        db_table = 'de_anti_icing_types'

    def __str__(self):
        return f'{self.name}'