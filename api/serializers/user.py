from rest_framework import serializers

from user.models import PersonDetails, Person, PersonRole, UserSettings


class PersonDetailsSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = PersonDetails
        fields = ['contact_email', 'contact_phone', 'title',
                  'first_name', 'middle_name', 'last_name', ]

    def get_title(self, obj):
        return obj.title.name if obj.title else ''


class PersonSerializer(serializers.ModelSerializer):
    details = PersonDetailsSerializer()
    is_staff = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ['id', 'details', 'initials', 'is_staff', ]

    def get_is_staff(self, obj):  # noqa
        if hasattr(obj, 'user'):
            return obj.user.is_staff


class PersonRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = PersonRole
        fields = ['id', 'name', ]


class UserSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserSettings
        exclude = ['id', 'user']
