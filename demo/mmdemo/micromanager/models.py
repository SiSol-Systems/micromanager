#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    MICROMANAGER - template first content management
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.conf import settings
from django.apps import apps
from django.utils import translation
from django.utils.html import strip_tags
from django.template.defaultfilters import slugify
from django.template import loader
from django import forms
try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse
from django.core.files import File 

from django.utils.translation import ugettext as _

#from slugifier.slugifier import create_unique_slug

from anytag.models import TaggedItem

import os, shutil, json
from datetime import datetime

from micromanager.widgets import MultiContentWidget
from micromanager.fields import MultiContentField

from django.utils.safestring import mark_safe


def _get_themes_root():
    micromanagerpath = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(micromanagerpath, "themes")

def _get_themes():

    themes_path = _get_themes_root()

    themes = []

    # iterate over all folders
    for root, dirs, files in os.walk(themes_path):
        for d in dirs:
            settings_file = os.path.join(root, d, "settings.json")

            if os.path.isfile(settings_file):
                with open(settings_file, "r") as f:
                    settings = json.load(f)

                theme = (d, settings["name"])
                themes.append(theme)

    return themes

INSTALLED_THEMES = _get_themes()

class CMSManager(models.Manager):
    
    def create(self, name, theme, language):
        
        cms = self.model(
            name = name,
            theme = theme,
        )
        cms.save()

        cms_lang = CMSLanguages(
            language = language,
            cms = cms,
            is_primary = True
        )
        cms_lang.save()

        return cms


class CMS(models.Model):
    name = models.CharField(max_length=100)
    theme = models.CharField(max_length=255, choices=INSTALLED_THEMES)

    objects = CMSManager()

    def primary_language(self):
        return CMSLanguages.objects.get(cms=self, is_primary=True).language

    def secondary_languages(self):
        languages = list(CMSLanguages.objects.filter(cms=self, is_primary=False).values_list("language", flat=True))
        return languages

    def languages(self):
        return CMSLanguages.objects.filter(cms=self)

    def get_language(self):
        
        locale = translation.get_language()

        if locale is not None:
            locale = locale[:2].lower()
        else:
            locale = "en"

        languages = CMSLanguages.objects.filter(cms=self)

        if locale in languages.values_list("language", flat=True):
            return locale
        else:
            return languages.get(is_primary=True).language

        
    def load_theme_settings(self):
        theme_settings = {}
        
        settings_path = os.path.join(_get_themes_root(), self.theme, "settings.json")

        if os.path.isfile(settings_path):
            with open(settings_path, "r") as f:
                theme_settings = json.loads(f.read())

        return theme_settings


    def get_theme_path(self):
        return os.path.join(_get_themes_root(), self.theme)


    def get_templates_path(self):
        return os.path.join(self.get_theme_path(), "templates")

    def delete(self, *args, **kwargs):
        folder = os.path.join(settings.MEDIA_ROOT, 'micromanager', str(self.pk))
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        return super(CMS, self).delete(*args, **kwargs)


    def get_templates(self, template_type):

        templates_path = os.path.join(self.get_templates_path(), template_type)
        settings = self.load_theme_settings()
        language = self.get_language()

        templates = []
    
        for filename in os.listdir(templates_path):

            template_path = "%s/%s" % (template_type, filename)
            verbose_name = template_path

            if template_path in settings['verbose_template_names'] and language in settings['verbose_template_names'][template_path]:
                verbose_name = settings['verbose_template_names'][template_path][language]

            templates.append((template_path, verbose_name))

        return templates
        
        
    def get_page_templates(self):
        return self.get_templates('page')

    def get_content_templates(self):
        return self.get_templates('content')


# the languages the website supports
class CMSLanguages(models.Model):
    language = models.CharField(max_length=15, choices=settings.LANGUAGES) # length like in django_parler
    cms = models.ForeignKey(CMS)
    is_primary = models.BooleanField(default=False)

    def save(self, *args, **kwargs):

        if self.is_primary == True:
            old_primary = CMSLanguages.objects.filter(cms=self.cms, is_primary=True).first()
            if old_primary:
                old_primary.is_primary = False
                old_primary.save()

        return super(CMSLanguages, self).save(*args,**kwargs)


    class Meta:
        unique_together = ('cms', 'language')



"""
    a TamplateContent consists of content_type and a template
    in the admin, micromanager displays all template_content templates in {theme_name}/templates/content/*
"""
class TemplateContentManager(models.Manager):

    # template_contents are always created in the primary language
    def create(self, creator, cms, title, template_name, template_type):
        
        template_content = self.model(
            cms = cms,
            template_name = template_name,
            template_type = template_type,
        )
        template_content.save()

        language = cms.primary_language()

        localized_template_content = LocalizedTemplateContent.objects.create(creator, template_content, language, title)

        return template_content
    

'''
    there are two template types:
    - page: extends a base.html
    - content: can be displayed on a page
'''
TEMPLATE_TYPES = (
    ('page', _('Page')),
    ('content', _('Content')),
)
class TemplateContent(models.Model):
    cms = models.ForeignKey(CMS)
    template_name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    draft_version = models.IntegerField(default=1)
    published_version = models.IntegerField(null=True)
    published_at = models.DateTimeField(null=True)
    is_home_page = models.BooleanField(default=False)

    objects = TemplateContentManager()

    def verbose_template_name(self):
        language = self.cms.get_language()
        settings = self.cms.load_theme_settings()

        verbose_name = self.template_name

        if self.template_name in settings['verbose_template_names'] and language in settings['verbose_template_names'][self.template_name]:
            verbose_name = settings['verbose_template_names'][self.template_name][language]

        return verbose_name
        

    def get_localized(self, language):
        localized_template_content = LocalizedTemplateContent.objects.filter(template_content=self, language=language).first()
        return localized_template_content

    def locales(self):
        return LocalizedTemplateContent.objects.filter(template_content=self)

    def template_path(self):
        return os.path.join(self.cms.get_templates_path(), self.template_name)

    def get_template(self):
        t = loader.get_template(self.template_name)
        return t.template

    def primary_title(self):
        locale = LocalizedTemplateContent.objects.filter(template_content=self, language=self.cms.primary_language()).first()

        if locale:
            return locale.title
        else:
            return None

    def translation_complete(self):
        for language in self.cms.languages():
            lp = LocalizedTemplateContent.objects.filter(template_content=self, language=language.language).first()

            if not lp:
                return False

            if not lp.translation_ready:
                return False

            if not lp.translation_complete():
                return False
            
        return True


    def publish(self, language="all"):

        publication_errors = []
        
        if not self.translation_complete():
            publication_errors.append(_("The texts of this content or its translations (if any) are not yet complete."))

        # below this, no error checks are allowed because published_versions are being set

        if not publication_errors:

            if language == "all":
                lps = LocalizedTemplateContent.objects.filter(template_content=self)
            else:
                lps = [LocalizedTemplateContent.objects.get(template_content=template_content, language=language)]

            for lp in lps:
                lp.save(publish=True)

            self.save(publish=True)

        return publication_errors
    

    def types(self):
        return TemplateContentTypes.objects.filter(template_content=self).values_list("content_type", flat=True)


    def save(self, *args, **kwargs):

        publish = kwargs.pop("publish", False)

        if publish:
            if self.published_version == self.draft_version:
                self.published_version +=1
                self.draft_version += 1
            else:
                self.published_version = self.draft_version

            if not self.published_at:
                self.published_at = datetime.now()

        else:
            if self.draft_version == self.published_version:
                self.draft_version += 1

        super(TemplateContent, self).save(*args, **kwargs)


class LocalizedTemplateContentManager(models.Manager):

    def create(self, creator, template_content, language, title):
        
        slug = self.generate_slug(title)

        localized_template_content = self.model(
            creator = creator,
            template_content = template_content,
            language = language,
            title = title,
            slug = slug,
        )
        
        localized_template_content.save()

        return localized_template_content


    def generate_slug(self, title):
        max_len = 30
        slug_base = str('%s' % (slugify(title)) )[:max_len-1]

        slug = slug_base

        exists = LocalizedTemplateContent.objects.filter(slug=slug).exists()

        i = 2
        while exists:
            
            if len(slug) > max_len:
                slug_base = slug_base[:-1]
                
            slug = str('%s%s' % (slug_base, i))
            i += 1
            exists = LocalizedTemplateContent.objects.filter(slug=slug).exists()

        return slug

"""
    translation_ready is set by the translator to signal that he has finished the translation
"""
class LocalizedTemplateContent(models.Model):
    template_content = models.ForeignKey(TemplateContent)
    slug = models.SlugField(unique=True)# localized slug
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="template_content_creator")
    last_modified = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    draft_version = models.IntegerField(null=True)
    published_version = models.IntegerField(null=True)
    translation_ready = models.BooleanField(default=False)

    tags = GenericRelation(TaggedItem) # localized

    objects = LocalizedTemplateContentManager()

    def save(self, *args, **kwargs):

        publish = kwargs.pop("publish", False)

        if publish:
            
            microcontents = MicroContent.objects.filter(template_content=self.template_content)
            for mc in microcontents:
                mc.publish(self.language)

            content_images = ContentImages.objects.filter(template_content=self.template_content)
            for cimg in content_images:
                cimg.publish(self.language)

            self.published_version = self.template_content.draft_version

        else:
            # the template_content has been published
            # all localized template_contents and the template_content have the same published_version
            # AND the localized template_contents and the template_content have the same draft_version
            if self.published_version == self.template_content.published_version:

                # check if the template_contents draft version has to be increased
                if self.template_content.draft_version == self.template_content.published_version:
                    self.template_content.draft_version += 1
                    self.template_content.save()

                if self.draft_version == self.published_version:
                    self.draft_version = self.template_content.draft_version
                    self.translation_ready = False

        super(LocalizedTemplateContent, self).save(*args, **kwargs)


    def get_microcontent(self, content_type):
        return MicroContent.objects.filter(template_content=self.template_content, content_type=content_type)


    def translation_complete(self):

        if not self.translation_ready:
            return False

        if self.draft_version != self.template_content.draft_version:
            return False
        
        # load the parser
        from .parser import TemplateParser
        parser = TemplateParser(self.template_content.get_template())

        cms_tags = parser.parse()

        for tag in cms_tags:
            if not "optional" in tag.args:
                
                content = tag.Model.objects.filter(template_content=self.template_content, content_type=tag.content_type).first()

                if not content:
                    return False

                else:
                    complete = content.translation_complete(self.language, tag)
                    if not complete:
                        return False
        
        return True

    def types(self):
        return self.template_content.types()


'''
    assign types to template_content, like 'footer' or 'page'
    multiple assignments possible
'''
class TemplateContentTypes(models.Model):
    template_content = models.ForeignKey(TemplateContent)
    content_type = models.CharField(max_length=255) # e.g. 'page', 'footer', 'homepage'
    position = models.IntegerField(default=1)

    class Meta:
        unique_together = ("template_content", "content_type")


"""
    MICROCONTENT
    - linked to a template_content (there can be multiple template_contents of the same type)
    - 1:n relation
    - separates layout from text/images
"""
class CMSMicroContentManager(models.Manager):

    def create(self, localized_template_content, content_type, content, editor, **kwargs):
        raise NotImplementedError("CMSMicrocontent needs a Manager with appropriate create method")

    def get_language_depandant(self, localized_template_content, content_type, content, editor, **kwargs):
        raise NotImplementedError("CMSMicrocontent needs a Manager with appropriate get_localized method")
            
    
"""
    case:
    - user creates a new template_content version
    - in the new version he deletes a content
    - the content has to remain in the db until he publishes the new version
"""
class CMSMicroContent(models.Model):
    template_content = models.ForeignKey(TemplateContent, null=True) # if template_content is None, it is the same content for every template_content
    deleted = models.BooleanField(default=False)
    deleted_in_template_content_version = models.IntegerField(null=True)
    content_type = models.CharField(max_length=255)
    position = models.IntegerField(default=1)

    objects = CMSMicroContentManager()

    def get_content(self, language, draft=False):
        raise NotImplementedError("CMSMicroContent need a get_content method")

    def set_content(self, content, editor, language):
        raise NotImplementedError("CMSMicroContent need a set_content method")

    def get_localized(self, language):
        raise NotImplementedError("CMSMicroContent need a get_localized method")

    def get_form_field(self, widget_attrs, *args, **kwargs):
        raise NotImplementedError("CMSMicroContent need a get_form_field method")

    def translation_complete(self, language):
        raise NotImplementedError("CMSMicroContent need a translation_complete method")

    def publish(self, language):
        raise NotImplementedError("CMSMicroContent need a publish method")


    def save(self):
        self.template_content.save()
        super(CMSMicroContent, self).save()

    def delete(self, *args, **kwargs):
        if self.template_content.published_version == None or self.template_content.published_version > self.deleted_in_template_content_version: 
            super(CMSMicroContent, self).delete(*args, **kwargs)
        else:
            self.deleted = True
            self.deleted_in_template_content_version = self.template_content.draft_version
            self.save()
            

    class Meta:
        abstract = True

    
"""
    MicroContent
    - are parts of template_contents that the user can fill with text
    - is restricted to one template_content
    - can have one or more images linked to it
    - can be layoutable or not
"""
class MicroContentManager(CMSMicroContentManager):

    def create(self, template_content, language, content_type, content, editor, **kwargs):

        microcontent = self.model(
            template_content = template_content,
            content_type = content_type,
        )

        microcontent.save()

        localized_content = LocalizedMicroContent.objects.create(microcontent, language, content, editor)

        return microcontent
    
    # return CMSMicroContent instances
    def get_language_dependant(self, template_content, content_type, language):

        contents = []

        contents_ = self.filter(template_content=template_content, content_type=content_type)

        for content in contents_:
            lmc = LocalizedMicroContent.objects.filter(microcontent=content, language=language).first()

            if lmc is not None:
                contents.append(content)

        return contents


class MicroContent(CMSMicroContent):
    objects = MicroContentManager()

    def publish(self, language):
        lmc = LocalizedMicroContent.objects.filter(microcontent=self, language=language).first()
        if lmc:
            lmc.published_content = lmc.draft_content
            lmc.save()

    def get_content(self, language, draft=False):

        lmc = LocalizedMicroContent.objects.filter(microcontent=self, language=language).first()

        if lmc:
            if draft == True:
                return mark_safe(lmc.draft_content)
            else:
                if lmc.published_content:
                    return mark_safe(lmc.published_content)

        return None


    def get_localized(self, language):
        return LocalizedMicroContent.objects.filter(microcontent=self, language=language).first()


    def get_form_field(self, widget_attrs, *args, **kwargs):

        widget = forms.Textarea

        if "short" in args:
            widget = forms.TextInput

        if "multi" in widget_attrs:
            # assign the number
            widget_attrs["widget"] = widget
            return MultiContentField(widget=MultiContentWidget(widget_attrs), **kwargs)

        else:
            kwargs["widget"] = widget
            return forms.CharField(**kwargs)


    def set_content(self, content, editor, language):
        lmc = LocalizedMicroContent.objects.filter(microcontent=self, language=language).first() # unqiue_together
        if not lmc:
            lmc = LocalizedMicroContent.objects.create(self, language, content, editor)
        else:
            lmc.draft_content = content
            lmc.last_modified_by = editor
            lmc.save()


    def translation_complete(self, language, tag):
        lmc = LocalizedMicroContent.objects.filter(microcontent=self, language=language).first()

        if lmc:
            if lmc.draft_content is None or len(lmc.draft_content) == 0:
                return False

            return True

        return False


class LocalizedMicroContentManager(models.Manager):

    def create(self, microcontent, language, content, editor, **kwargs):

        localized_content = self.model(
            language = language,
            microcontent = microcontent,
            draft_content = content,
            creator = editor,
            **kwargs
        )

        localized_content.save()

        return localized_content


class LocalizedMicroContent(models.Model):
    microcontent = models.ForeignKey(MicroContent)
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)
    draft_content = models.TextField(null=True)
    published_content = models.TextField(null=True)
    plain_text = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="content_creator")
    last_modified = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)

    objects = LocalizedMicroContentManager()

    def save(self, *args, **kwargs):
        
        if self.draft_content is not None:
            self.plain_text = _generate_plaintext(self.draft_content)
        else:
            self.plain_text = None
             
        return super(LocalizedMicroContent, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        folder = self.get_dump_folder()
        if folder is not None and os.path.isdir(folder):
            shutil.rmtree(folder)
        return super(LocalizedMicroContent, self).delete(*args, **kwargs)


    class Meta:
        unique_together = ("microcontent", "language")


"""
    images directly linked to MicroContent or LocalizedMicroContent
"""
""" postponed
class MicroContentImages(models.Model):
    microcontent = models.ForeignKey(MicroContent)
    draft_content = models.ImageField()
    published_content = models.ImageField(null=True)
    

class LocalizedMicroContentImages(models.Model):
    localized_microcontent = models.ForeignKey(LocalizedMicroContent)
    draft_content = models.ImageField()
    published_content = models.ImageField(null=True)

"""
"""
    Images that are CMSMicroContent themselves - and not locale specific
"""
class ContentImagesManager(CMSMicroContentManager):

    def create(self, template_content, language, content_type, content, editor, **kwargs):

        microcontent = self.model(
            template_content = template_content,
            content_type = content_type,
            draft_content = content,
            creator = editor,
        )

        microcontent.save()

        return microcontent


    def get_language_dependant(self, template_content, content_type, language):

        return self.filter(template_content=template_content, content_type=content_type)


def content_images_upload_path(instance, filename):

    if hasattr(instance, "template_content") and instance.template_content is not None:
        subfolder = str(instance.template_content.cms.pk)
    else:
        subfolder = "global"

    path = os.path.join("micromanager", subfolder, "cms", "content_images",
                        instance.content_type, filename)
    
    return path


def content_images_publication_path(instance, filename):

    if hasattr(instance, "template_content") and instance.template_content is not None:
        subfolder = str(instance.template_content.cms.pk)
    else:
        subfolder = "global"

    path = os.path.join("micromanager", subfolder, "cms", "content_images",
                        instance.content_type, "published", filename)
    
    return path

        
class ContentImages(CMSMicroContent):
    draft_content = models.ImageField(upload_to=content_images_upload_path)
    published_content = models.ImageField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="image_creator")
    last_modified = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)

    objects = ContentImagesManager()

    def publish(self, language):
        
        if not self.published_content:
            self.published_content.save(
                content_images_publication_path(self, os.path.basename(self.draft_content.name)),
                File(open(self.draft_content.path, "r"))
            )
            self.save()


    def get_form_field(self, widget_attrs, *args, **kwargs):
        widget_attrs["file"] = self.draft_content
        reverse_kwargs = {
            "content_category" : widget_attrs["data-category"],
            "content_type" : widget_attrs["data-contenttype"],
        }
        widget_attrs["data-url"] = reverse("upload_image", kwargs=reverse_kwargs)
        return forms.ImageField(widget=forms.FileInput(widget_attrs), **kwargs)


    def get_content(self, language, draft=False):
        if draft == True:
            return self.draft_content
        else:
            if self.published_content:
                return self.published_content

        return None

    def get_localized(self, language):
        return self

    def set_content(self, content, editor, language):
        self.last_modified_by = editor
        old_filepath = self.draft_content.path
        
        self.draft_content = content
        self.save()

        if old_filepath != self.draft_content.path:
            if os.path.isfile(old_filepath):
                os.remove(old_filepath)

    def translation_complete(self, language, tag):
        return True



def _generate_plaintext(text):
    text = strip_tags(text)
    return ' '.join(text.split())


content_category_model_map = {
    'template_content' : TemplateContent,
    'template_contents' : TemplateContent,
    'microcontent' : MicroContent,
    'microcontents' : MicroContent,
    'image' : ContentImages,
    'images' : ContentImages,
}
