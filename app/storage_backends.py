from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.storage import FileSystemStorage
from django.conf import settings

class AirCardPhotoStorage(S3Boto3Storage):
    location = 'air_card_photos'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class OrderAirCardDocumentStorage(FileSystemStorage):
    '''
    Storage stores OrderAirCardDocument model's files
    '''
    location = f'{settings.DOCS_ROOT}/AirCardDocumentFiles'


class ClientDocumentStorage(FileSystemStorage):
    '''
    Client document files
    '''
    location = f'{settings.DOCS_ROOT}/ClientDocumentFiles'


class ClientAgreementFileStorage(FileSystemStorage):
    '''
    Client Agreement files
    '''
    location = f'{settings.DOCS_ROOT}/ClientAgreementFiles'


class SPFSignaturesStorage(S3Boto3Storage):
    location = 'spf_signatures'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class SPFDocumentsStorage(S3Boto3Storage):
    location = 'spf_documents'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class AutoSPFDocumentsStorage(S3Boto3Storage):
    location = 'spf_auto_documents'
    file_overwrite = True
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class OrganisationsLogosStorage(S3Boto3Storage):
    location = 'organisations_logos'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class OrganisationDocumentStorage(S3Boto3Storage):
    location = 'organisation_documents'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class OrganisationPeopleActivityStorage(S3Boto3Storage):
    location = 'crm_activities_attachments'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class FuelReleaseStorage(S3Boto3Storage):
    location = 'handling_fuel_release'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class TaxRulesFileStorage(S3Boto3Storage):
    location = 'tax_rules_source_files'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800


class HandlingRequestDocumentFilesStorage(S3Boto3Storage):
    location = 'handling_documents'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 172800


class TravelDocumentFilesStorage(S3Boto3Storage):
    location = 'travel_documents'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 3600


class FuelPricingMarketPldDocumentFilesStorage(S3Boto3Storage):
    location = 'fuel_pricing_market_pld_documents'
    file_overwrite = False
    custom_domain = False
    default_acl = 'private'
    querystring_expire = 604800
