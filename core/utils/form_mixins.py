from django.forms import BaseForm


class FormValidationMixin(BaseForm):
    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                if self.fields[field].widget.__class__.__name__ == 'CheckboxInput':
                    existing_class = self.fields[field].widget.attrs['class']
                    self.fields[field].widget.attrs['class'] = f'{existing_class} is-invalid'
                else:
                    existing_class = self.fields[field].widget.attrs['class']
                    self.fields[field].widget.attrs['class'] = f'{existing_class} is-invalid'
        return is_valid
