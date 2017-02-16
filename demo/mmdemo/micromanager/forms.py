from django.conf import settings
from django import forms
from django.utils.translation import ugettext as _

import os

from micromanager.parser import TemplateParser
from micromanager.CMSObjects import Theme
from micromanager.models import INSTALLED_THEMES, CMSLanguages

from django.template import loader

from django.contrib.auth import get_user_model

User = get_user_model()


class CreateTemplateContentForm(forms.Form):

    title = forms.CharField()
    template_name = forms.ChoiceField(label =_("Template"))

    def __init__(self, *args, **kwargs):

        cms = kwargs.pop('cms', None)
        template_type = kwargs.pop('template_type', None)

        if cms is None:
            raise ValueError('cms not found in kwargs of CreateTemplateContentForm')

        if template_type is None:
            raise ValueError('template_type not found in kwargs of CreateTemplateContentForm')
        
        super(CreateTemplateContentForm, self).__init__(*args, **kwargs)

        # load the template_choices according to the cms
        choices = cms.get_templates(template_type)
        self.fields['template_name'].choices = choices



"""
    there are global contents without page (eg on base.html)
    and contents bound to a page    
"""
class ManageMicroContentsForm(forms.Form):

    language = forms.CharField(widget=forms.HiddenInput)

    def _append_additional_fields(self):
        pass

    def _template(self):
        return self.template_content.get_template()

    def __init__(self, template_content, language, *args, **kwargs):

        self.template_content = template_content
        self.language = language

        for_translation = kwargs.pop("for_translation", False)
        
        super(ManageMicroContentsForm, self).__init__(*args, **kwargs)

        self._append_additional_fields()

        self.layoutable_full_fields = set([])
        self.layoutable_simple_fields = set([])

        # read the template and find microcontent
        template = self._template()

        # find all cms template tags in source
        parser = TemplateParser(template)
        cms_tags = parser.parse()

        # the fields should be in self.fields        
        for tag in cms_tags:

            # get cms form fields for each tag
            for field in tag.form_fields(language, template_content, for_translation=for_translation):
                
                self.fields[field["name"]] = field["field"]
                
                if "layoutable-simple" in tag.args:
                    self.layoutable_simple_fields.add(field["name"])
                elif "layoutable-full" in tag.args:
                    self.layoutable_full_fields.add(field["name"])


class ManageTemplateContentForm(ManageMicroContentsForm):
    
    title = forms.CharField()
    is_home_page = forms.BooleanField(required=False)
    page_types = forms.MultipleChoiceField(label=_('Show in'), required=False)


    def _append_additional_fields(self):
        # read the theme conf and add the page types defined there
        theme = Theme(self.template_content.cms.theme)

        page_type_choices = []
        for tp in theme.settings["navigations"]:
            page_type_choices.append(
                (tp, _(tp))
            )

        for section, definition in theme.settings['sections'].items():
            page_type_choices.append(
                (section, _(section))
            )

        if self.template_content.template_type == 'pages':
            self.fields['page_types'].choices = page_type_choices
        else:
            self.fields.pop('page_types')
            self.fields.pop('is_home_page')


class TranslatePageForm(ManageMicroContentsForm):
    title = forms.CharField()


class ManagePagebaseForm(ManageMicroContentsForm):

    def __init__(self, template, language, *args, **kwargs):
        self.template = template
        super(ManagePagebaseForm, self).__init__(None, language, *args, **kwargs)

    def _template(self):
        return self.template
    
# the Page with template_name base.html
class ThemeSettingsForm(forms.Form):
    theme = forms.ChoiceField(choices=INSTALLED_THEMES)
        
        
class DeleteContentForm(forms.Form):
    pk = forms.IntegerField(widget=forms.HiddenInput)
    content_category = forms.CharField(widget=forms.HiddenInput)
    content_type = forms.CharField(widget=forms.HiddenInput, required=False)


class UploadFileForm(forms.Form):
    # used urlparam instead: if form is invalid render an empty input with error message
    # content_category = forms.CharField()
    # content_type = forms.CharField()
    pk = forms.IntegerField(required=False)
    template_content_id = forms.IntegerField(required=False)
    language = forms.ChoiceField(widget=forms.HiddenInput, choices=settings.LANGUAGES)
    file = forms.FileField()


class UploadImageForm(UploadFileForm):
    file = forms.ImageField()

        
class AddLanguageForm(forms.ModelForm):
    class Meta:
        model = CMSLanguages
        fields = ("language",)
    

from .models import _get_themes
class FirstTimeSetupForm(forms.Form):
    cms_name = forms.CharField(label=_('Name of your website'))
    primary_language = forms.ChoiceField(choices=settings.LANGUAGES,
                                         help_text=_('You can set additional languages later'))

    theme = forms.ChoiceField(choices=_get_themes())


'''
    create a superuser account with email
'''
from django.contrib.auth.forms import UserCreationForm
from .compatibility import UsernameField
class CreateAdminForm(UserCreationForm):

    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'email_mismatch': _("The two email address fields didn't match."),
    }
    
    email = forms.EmailField(label=_('e-mail'))
    email2 = forms.EmailField(label = _('e-mail (again)'))

    def clean_email2(self):
        email = self.cleaned_data.get("email")
        email2 = self.cleaned_data.get("email2")
        if email and email2 and email != email2:
            raise forms.ValidationError(
                self.error_messages['email_mismatch'],
                code='email_mismatch',
            )
        
        return email2


    def save(self, commit=True):
        # create the superuser from ModelManager
        user = User.objects.create_superuser(self.cleaned_data['username'], self.cleaned_data['email'],
                                             self.cleaned_data['password1'])
        return user


    class Meta:
        model = User
        fields = ("username", "email", "email2")
        field_classes = {'username': UsernameField}
        

