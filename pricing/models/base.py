from core.models.settings import GlobalConfiguration


class Permissions(GlobalConfiguration):
    class Meta:
        proxy = True

        permissions = [
            ('p_view', 'Data Management: View Fuel Indices, Fuel Agreements, Agreement and Market Pricing'),
            ('p_create', 'Data Management: Create Fuel Indices, Fuel Agreements, Agreement and Market Pricing'),
            ('p_update', 'Data Management: Update Fuel Indices, Fuel Agreements, Agreement and Market Pricing'),
            ('p_moderate', 'Data Management: Review Created Supplier Fuel Agreements and Pricing - Acceptance Review'),
            ('p_publish', 'Data Management: (Un-)Publish Fuel Indices, Fuel Agreements, Agreement and Market Pricing'),
            ('p_send_pricing_update_request', 'Data Management: Send Auto-generated Pricing Update Request Emails'),
        ]
