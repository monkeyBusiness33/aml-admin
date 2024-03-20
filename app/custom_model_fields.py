import uuid
import datetime
import posixpath

from django.db.models.fields import UUIDField
from django.db.models.fields.files import FileField
from django.core.files.utils import validate_file_name
from django.utils.translation import gettext_lazy as _

class FullUUIDField(UUIDField):
    '''
    Custom UUID field to return full UUID instead it's hex for the MySQL
    This is implemented firstly for the OrderAirCardDocument model
    '''
    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = self.to_python(value)

        if connection.features.has_native_uuid_field:
            return value
        # Changed to output full UUID instead .hex
        return value


class PkFilenameFileField(FileField):
    '''
    Custom file field that is saves file using PK field
    for the filename but original filename stored in the database
    // Workaround for the old AML file structure
    // Should be used in pair with modified UUIDDocumentDownloadView
    '''

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        original_filename = file.name
        if file and not file._committed:
            # Commit the file to storage prior to saving the model
            file.save(file.name, file.file, save=False)
        
        file.name = original_filename
        return file

    def generate_filename(self, instance, filename):
        """
        Apply (if callable) or prepend (if a string) upload_to to the filename,
        then delegate further processing of the name to the storage backend.
        Until the storage layer, all file paths are expected to be Unix style
        (with forward slashes).
        // Override original function to pass instance to the storage backend
        """

        dirname = datetime.datetime.now().strftime(str(self.upload_to))
        temp_filename = str(instance.pk) + str(instance.extension)
        filename = posixpath.join(dirname, temp_filename)
        filename = validate_file_name(filename, allow_relative_path=True)
        return filename
