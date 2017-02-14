from django import forms

from django.utils.translation import ugettext as _

from micromanager.models import content_category_model_map

import os, json

"""
    CMSTagObject is an object created from a template tag
    - the templatetag can allow multiple instances of CMSObjects
"""
class CMSTag(object):

    def __init__(self, content_category, content_type, *args, **kwargs):
        self.content_category = content_category
        self.content_type = content_type
        self.args = list(args)
        
        self.Model = content_category_model_map[content_category]

        self.multi = False
        self.min_num = kwargs.get("min", 0)
        self.max_num = kwargs.get("max", None)

        self.is_translatable = True

        # translatable images have their own content_category 
        if self.content_category in ["image", "images"]:
            self.is_translatable = False
        
        if "multi" in args:
            self.multi = True
            
        elif self.content_category in ["images", "microcontents"]:
            self.multi = True
            self.args.append("multi")


    """
    return a form field instance with an cms object attached to it
    """

    def _get_widget_attrs(self):
        widget_attrs = {
            "data-category" : self.content_category,
            "data-contenttype" : self.content_type,
            "data-type" : "%s-%s" % (self.content_category, self.content_type),
        }

        return widget_attrs
    
    def form_fields(self, language, template_content=None, **kwargs):

        for_translation = kwargs.get("for_translation", False)

        if for_translation == True and self.is_translatable == False:
            return []

        form_fields = []

        widget_attrs = self._get_widget_attrs()

        if self.multi:

            # the first of multiple fields
            is_first = True
            is_last = False
            
            # returns language dependant microcontent
            if for_translation == False:
                instances = self.Model.objects.get_language_dependant(template_content, self.content_type, language)
            else:
                # fetch all primary language instances
                instances = self.Model.objects.get_language_dependant(template_content, self.content_type, template_content.cms.primary_language())

            instance_count = len(instances)

            field_count = 0

            # add simple fields for existing content, enumerate, start counting at 1
            for counter, instance in enumerate(instances, 1):
                # add an empty field if max_num not reached yet
                if self.max_num is None or self.max_num <= counter:

                    # check if this is the last field
                    if self.max_num is not None and counter == self.max_num:
                        is_last = True
                    
                    field = self._create_field(language, instance, widget_attrs, is_first=is_first, is_last=is_last)
                    form_fields.append(field)
                    field_count += 1
                    is_first = False

            # add multi-value field for content / multi-image-field for images
            # there is always only one blank field
            if (self.max_num is None or field_count < self.max_num) and for_translation == False:
                # is_last is False
                is_last = True

                # append attrs to the widget
                widget_attrs.update({
                    "multi" : True,
                })
                    
                field = self._create_field(language, None, widget_attrs, is_first=is_first, is_last=is_last)
                form_fields.append(field)
                is_first = False

        else:
            # check if the cms object already exists, if so, use initial for the field
            instance = self.Model.objects.filter(template_content=template_content, content_type=self.content_type).first()
            field = self._create_field(language, instance, widget_attrs)
            form_fields.append(field)

        return form_fields


    # multi fields also pass is_first/is_last in kwargs
    def _create_field(self, language, instance=None, widget_attrs={}, **kwargs):

        widget_attrs = widget_attrs.copy()
        
        if instance is not None and instance.pk:
            field_name = "pk-%s-%s" %(instance.pk, self.content_type)
            widget_attrs["data-pk"] = instance.pk
        else:
            instance = self.Model()
            field_name = self.content_type

        field_kwargs = self._get_field_kwargs(language, instance=instance)
        field_kwargs["label"] = _(self.content_type)

        form_field = instance.get_form_field(widget_attrs, *self.args, **field_kwargs)
        if instance is not None and instance.pk:
            form_field.instance = instance
            
        form_field.cms_object = CMSObject(self.Model, self.content_category, self.content_type, self.multi,
                                            self.min_num, self.max_num, instance, *self.args, **kwargs)

        field = {
            "field" : form_field,
            "name" : field_name, 
        }

        return field
        
    

    def _get_field_kwargs(self, language, instance=None):
        kwargs = {
            "required" : False, # fields are only required when publishing
        }

        if instance is not None and instance.pk:
            kwargs["initial"] = instance.get_content(language, draft=True)

        return kwargs           



"""
    content_categories are template_content(TemplateContent), microcontent(MicroContent), image(ContentImage)
"""

class CMSObject(object):

    def __init__(self, Model, content_category, content_type, multi, min_num, max_num, instance, *args, **kwargs):
        self.content_category = content_category
        self.content_type = content_type
        self.args = args        
        self.Model = content_category_model_map[content_category]
        self.multi = multi
        self.min_num = min_num
        self.max_num = max_num
        self.is_file = "image" in self.content_category
        self.instance = instance
        self.kwargs = kwargs


class Theme(object):

    def __init__(self, theme_name):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.dir_path = os.path.join(dir_path, "themes", theme_name)

        if not os.path.isdir(self.dir_path):
            raise FileNotFoundError("The theme %s could not be found." % theme_name)

        settings_file_path = os.path.join(self.dir_path, "settings.json")

        if not os.path.isfile(settings_file_path):
            raise FileNotFoundError("settings file for theme %s could not be found." % theme_name)

        with open(settings_file_path, "r") as f:
            self.settings = json.load(f)
