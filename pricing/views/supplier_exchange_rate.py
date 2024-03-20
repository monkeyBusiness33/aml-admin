from decimal import Decimal

from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from pricing.models import SupplierFuelFeeRate, FuelType, PricingUnit
from user.mixins import AdminPermissionsMixin


class ApplySupplierExchangeRateAjaxView(AdminPermissionsMixin, View):
    permission_required = ['pricing.p_view']

    @staticmethod
    def apply_supplier_xr(uom_from, uom_to, xr_override, fuel):
        # Replicate some of the validation, so that relevant errors are displayed
        # when there is an issue with application of the supplier exchange rate
        # (we return first encountered error)

        # Fixed rates can only be converted into fixed rates
        if uom_from.uom.is_fluid_uom != uom_to.uom.is_fluid_uom:
            raise ValueError('Fixed and unit rates cannot be converted between.')

        # Volume to mass and vice versa conversions are impossible if no specific fuel selected
        if fuel is None and any([uom_from.uom.is_volume_uom != uom_to.uom.is_volume_uom,
                                 uom_from.uom.is_mass_uom != uom_to.uom.is_mass_uom]):
            raise ValueError('Mass and volume unit rates can only be converted'
                             ' between if a specific fuel type is provided.')

        # Use the SupplierFuelFeeRate object's method to calculate the conversion
        fee_obj = SupplierFuelFeeRate()
        fee_obj.specific_fuel = fuel
        fee_obj.pricing_native_amount = 1
        fee_obj.pricing_native_unit = uom_from
        fee_obj.pricing_converted_unit = uom_to
        fee_obj.supplier_exchange_rate = xr_override
        fee_obj.convert_pricing_amount()

        return fee_obj.pricing_converted_amount

    def post(self, request, *args, **kwargs):
        fuel_pk = request.POST.get('fuel_pk')
        native_unit_pks = request.POST.getlist('native_unit_pk[]')
        converted_unit_pk = request.POST.get('converted_unit_pk')
        supplier_xr = Decimal(request.POST.get('supplier_xr'))

        fuel = get_object_or_404(FuelType, pk=fuel_pk) if fuel_pk else None
        native_units = PricingUnit.objects.filter(pk__in=native_unit_pks)
        converted_unit = get_object_or_404(PricingUnit, pk=converted_unit_pk)

        try:
            # Validation: Conversion can only be applied, if all locations use the same currency
            native_currs = {c.currency for c in native_units}

            if len(native_currs) > 1:
                raise ValueError('Supplier currency override can only be used if all locations'
                                 ' covered by the fee use the same currency.')

            rates = [{
                'from': u.description_short,
                'to': converted_unit.description_short,
                'rate': '{:f}'.format(self.apply_supplier_xr(u, converted_unit, supplier_xr, fuel).normalize()),
                'fuel': fuel.name if fuel else None,
            } for u in native_units]
        except Exception as e:
            import sentry_sdk
            sentry_sdk.capture_exception(e)

            return JsonResponse({
                'success': 'false',
                'msg': str(e),
            })

        return JsonResponse({
            'success': 'true',
            'rates': rates,
        })
