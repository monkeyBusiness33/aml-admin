from .models.comment import Comment, CommentReadStatus
from django import forms
from django.db import transaction
from django.forms import widgets
from django.core.validators import RegexValidator
from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax


phone_validator_error_message = 'Phone number should start from "+", may contains spaces and brackets'
phone_regex_validator = RegexValidator(
    regex=r'^(\+?\0?)(\s?)+\d(\s?\(?\d\)?){6,26}$',
    message=phone_validator_error_message
)


class ConfirmationForm(BSModalForm):
    """
    Empty form for confirmation dialogs
    """


class MultiButtonConfirmationFormMixin(forms.Form):
    """
    Form mixin to add "Multi Button" confirmation ability
    Provides boolean hidden input to have "Accept/Decline" buttons
    """
    multi_button = forms.TypedChoiceField(coerce=lambda x: x == 'True',
                                          choices=((False, 'No'),
                                                   (True, 'Yes')),
                                          widget=widgets.HiddenInput(),
                                          label=False,
                                          required=False)


class MultiButtonConfirmationForm(MultiButtonConfirmationFormMixin, BSModalForm):
    """
    Multi Button confirmation form
    """


class CommentForm(BSModalModelForm):

    class Meta:
        model = Comment
        fields = ['text', 'is_pinned', ]
        widgets = {
            "text": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
            "is_pinned": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def save(self, commit=True):
        """
        For S&F Request comments (Mil Team Notes), on Comment creation create a CommentReadStatus
        with is_read set to False for each existing member of the Mil Team (with 'Military Team' role),
        except the author, for whom it's set to True.
        """
        comment = super().save()

        if comment.handling_request is None:
            return comment

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():
                    from user.models.person import Person

                    mil_team_members = Person.objects.filter(user__roles=1000)
                    new_statuses = []

                    for member in mil_team_members:
                        new_statuses.append(CommentReadStatus(
                            person=member,
                            comment=comment,
                            is_read=member.pk == self.request.user.person.pk
                        ))

                    CommentReadStatus.objects.bulk_create(new_statuses)

        return comment


class NumberedMultiButtonFormMixin(forms.Form):
    """
    Form mixin provides two button form with typed (int) value for each button
    """
    multi_button = forms.TypedChoiceField(coerce=int,
                                          choices=((1, 'Option #1'),
                                                   (2, 'Option #2')),
                                          widget=widgets.HiddenInput(),
                                          label=False,
                                          required=False)


class NumberedMultiButtonFormConfirmationForm(NumberedMultiButtonFormMixin, BSModalForm):
    """
    Numbered value Multi Button confirmation form
    """


class ClearableMultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
