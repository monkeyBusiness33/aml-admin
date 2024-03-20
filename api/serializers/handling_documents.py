from tempfile import NamedTemporaryFile

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from datetime import datetime

from api.serializers.user import PersonSerializer
from api.utils.related_field import RelatedFieldAlternative
from handling.models import HandlingRequestDocumentType, HandlingRequestDocument, HandlingRequestDocumentFile
from handling.tasks import invoice_signing_notifications
from handling.utils.document_signing import sign_document


class HandlingRequestDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequestDocumentType
        fields = ['id', 'name', ]


class HandlingRequestDocumentFileSerializer(serializers.ModelSerializer):
    uploaded_by = PersonSerializer()
    signed_by = PersonSerializer()

    class Meta:
        model = HandlingRequestDocumentFile
        fields = ['file', 'is_recent', 'uploaded_at', 'uploaded_by', 'is_signed', 'signed_by', ]


class HandlingRequestDocumentSerializer(serializers.ModelSerializer):
    type_id = RelatedFieldAlternative(required=True,
                                      write_only=True,
                                      source='type',
                                      queryset=HandlingRequestDocumentType.objects.all())
    type = HandlingRequestDocumentTypeSerializer(many=False, read_only=True)
    file = serializers.FileField(write_only=True, required=False)
    files = HandlingRequestDocumentFileSerializer(many=True, read_only=True)
    created_by = PersonSerializer(many=False, read_only=True)

    handling_request_id = serializers.IntegerField(required=False, write_only=True)
    mission_id = serializers.IntegerField(required=False, write_only=True)
    mission_leg_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = HandlingRequestDocument
        read_only_fields = ['type', 'created_at', 'is_staff_added', ]
        fields = ['id', 'type', 'type_id',
                  'description', 'is_staff_added',
                  'created_at', 'created_by',
                  'file', 'files',

                  'handling_request_id',
                  'mission_id',
                  'mission_leg_id',
                  ]

    def create(self, validated_data):
        request_person = getattr(self.context['request'].user, 'person')

        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        mission_id = None
        mission_leg_id = None

        if not handling_request_id:
            handling_request_id = validated_data.pop('handling_request_id', None)
            mission_id = validated_data.pop('mission_id', None)
            mission_leg_id = validated_data.pop('mission_leg_id', None)

            if not any([handling_request_id, mission_id, mission_leg_id]):
                raise serializers.ValidationError("Valid S&F Request, Mission or Flight Leg ID is required")

        # Check if user have access to the given organisation
        if not request_person.user.is_staff:
            position = request_person.primary_dod_position
            sfr_list = position.get_sfr_list(managed=True)
            missions = position.get_missions_list()

            if handling_request_id and not sfr_list.filter(pk=handling_request_id).exists():
                raise serializers.ValidationError(
                    detail={'handling_request_id': ["Invalid Handling Request ID."]})

            if mission_id and not missions.filter(pk=mission_id).exists():
                raise serializers.ValidationError(
                    detail={'mission_id': ["Invalid Mission ID."]})

            if mission_leg_id and not missions.filter(legs__id=mission_leg_id).exists():
                raise serializers.ValidationError(
                    detail={'mission_leg_id': ["Invalid Mission Leg ID."]})

        file = validated_data.pop('file', None)
        if not file:
            raise serializers.ValidationError(
                detail={'file': ["File attachment is required."]})

        with transaction.atomic():
            document = HandlingRequestDocument.objects.create(
                **validated_data,
                is_staff_added=request_person.user.is_staff,
                created_by=request_person,
                mission_id=mission_id,
                mission_leg_id=mission_leg_id,
                handling_request_id=handling_request_id)

            document_file = HandlingRequestDocumentFile()
            document_file.document = document
            document_file.uploaded_by = request_person
            document_file.file = file
            document_file.save()

        return document

    def update(self, instance, validated_data):
        request_person = getattr(self.context['request'].user, 'person')

        # Check if user have access to the given organisation
        if not request_person.user.is_staff:
            position = request_person.primary_dod_position

            document_available_qs = HandlingRequestDocument.objects.filter(
                Q(mission__in=position.get_missions_list()) |
                Q(mission_leg__mission__in=position.get_missions_list()) |
                Q(handling_request__in=position.get_sfr_list(managed=True)),
                pk=instance.pk,
            ).exists()

            if not document_available_qs:
                raise serializers.ValidationError("Document not found.")

            if instance.is_staff_added:
                raise serializers.ValidationError("Sorry, you can't amend document uploaded by staff.")

        file = validated_data.pop('file', None)

        document = super().update(instance, validated_data)

        if file:
            document_file = HandlingRequestDocumentFile()
            document_file.document = document
            document_file.uploaded_by = request_person
            document_file.file = file
            document_file.save()

        return document


class HandlingRequestDocumentSignSerializer(serializers.ModelSerializer):
    signature = serializers.FileField(write_only=True, required=True)
    type = HandlingRequestDocumentTypeSerializer(many=False, read_only=True)
    files = HandlingRequestDocumentFileSerializer(many=True, read_only=True)
    created_by = PersonSerializer(many=False, read_only=True)

    class Meta:
        model = HandlingRequestDocument
        read_only_fields = ['id', 'type', 'type_id',
                            'description', 'is_staff_added',
                            'created_at', 'created_by', 'files', ]

        fields = ['id', 'signature', 'type', 'type_id',
                  'description', 'is_staff_added',
                  'created_at', 'created_by', 'files', ]

    def update(self, instance, validated_data):
        request_person = getattr(self.context['request'].user, 'person')

        # Check if user have access to the given organisation
        if not request_person.user.is_staff:
            position = request_person.primary_dod_position
            missions = position.get_sfr_list()
            request_exists = missions.filter(pk=instance.handling_request.pk).exists()
            if not request_exists:
                raise serializers.ValidationError("Document not found.")

        document = self.instance
        signature = validated_data.get('signature')
        if not signature:
            raise serializers.ValidationError("Please submit signature file")

        # Create temporary file with signature
        signature_file = NamedTemporaryFile(suffix='.png')
        signature_file.write(signature.read())
        signature_file.seek(0)

        # Sign the document
        signed_pdf_file = sign_document(signature=signature_file, document=document, author=request_person)

        # Save signed document
        handling_request_document_file = document.recent_file
        handling_request_document_file.file.save(signed_pdf_file['name'], signed_pdf_file['file'])
        handling_request_document_file.is_signed = True
        handling_request_document_file.signed_by = request_person
        handling_request_document_file.signed_at = datetime.now()
        handling_request_document_file.save()

        invoice_signing_notifications.delay(document_id=document.pk)

        return document
