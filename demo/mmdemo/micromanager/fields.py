from django.forms.fields import Field, CharField
from django.forms.widgets import Textarea
from micromanager.widgets import MultiContentWidget
from django.core.exceptions import ValidationError

from django.utils.translation import ugettext_lazy as _


"""
    A field accepting multiple data of type CharField
    returns a list with data, or empty list
"""
class MultiContentField(Field):

    widget = MultiContentWidget

    default_error_messages = {
        'invalid': _('Enter valid text.')
    }

    def __deepcopy__(self, memo):
        result = super(MultiValueField, self).__deepcopy__(memo)
        result.fields = tuple(x.__deepcopy__(memo) for x in self.fields)
        return result

    def validate(self, value):
        pass

    def clean(self, value):
        """
        Validates every value in the given list.
        """
        clean_data = []
        errors = []
        if not value or isinstance(value, (list, tuple)):
            if not value or not [v for v in value if v not in self.empty_values]:
                if self.required:
                    raise ValidationError(self.error_messages['required'], code='required')
                else:
                    return []
        else:
            raise ValidationError(self.error_messages['invalid'], code='invalid')


        field = CharField()

        for field_value in value:
            try:
                clean_data.append(field.clean(field_value))
            except ValidationError as e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter. Skip duplicates.
                errors.extend(m for m in e.error_list if m not in errors)

            try:
                self.run_validators(field_value)
            except ValidationError as e:
                errors.extend(m for m in e.error_list if m not in errors)
        
        self.validate(clean_data)

        if errors:
            raise ValidationError(errors)
        
        return clean_data

    def has_changed(self, initial, data):
        for i in initial:
            if i not in data:
                return True

        return False
