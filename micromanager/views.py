from django.shortcuts import render, redirect
try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse
    
from django.views.generic.edit import FormView
from django.views.generic import DetailView, TemplateView, ListView
from django.utils.translation import ugettext as _
from django.http import Http404

import os, json

from django import forms
from micromanager.forms import (CreateTemplateContentForm, ManageTemplateContentForm, DeleteContentForm,
                                UploadImageForm, UploadFileForm, ThemeSettingsForm, AddLanguageForm,
                                ManagePagebaseForm, ManageMicroContentsForm, TranslatePageForm, FirstTimeSetupForm,
                                CreateAdminForm)

from micromanager.models import TemplateContent, LocalizedTemplateContent, TemplateContentTypes, content_category_model_map, CMS, CMSLanguages

from micromanager.mixins import AdminOnlyMixin

from micromanager.CMSObjects import CMSTag, Theme

from django.template import loader

from django.contrib.auth import get_user_model
User = get_user_model()

"""
    can be looked up by pk of template_content (not localizedPage) (primary language)
    or slug (language specific)
"""
class GenericPageView(DetailView):

    model = LocalizedTemplateContent
    context_object_name = "template_content"

    def get_object(self, queryset=None):

        if "pk" in self.kwargs:
            template_content = TemplateContent.objects.get(pk=self.kwargs["pk"])
            localized_template_content = LocalizedTemplateContent.objects.filter(template_content=template_content,
                                                        language=template_content.cms.get_language()).first()
        else:
            localized_template_content = LocalizedTemplateContent.objects.filter(slug=self.kwargs["slug"]).first()

        if not localized_template_content:
            raise Http404("TemplateContent not found")

        preview = self.request.GET.get("preview",False)
        if preview:
            return localized_template_content
        else:
            if localized_template_content.template_content.published_at == None:
                raise Http404("TemplateContent not found")

            return localized_template_content

    def get_context_data(self, **kwargs):
        context = super(GenericPageView, self).get_context_data(**kwargs)

        context["preview"] = bool(int(self.request.GET.get("preview",0)))
        context["template_content"] = self.object.template_content
        context["localized_template_content"] = self.object

        # set the base_template
        context["base_template"] = "base.html"

        # sections may use different base templates
        if "section" in kwargs:
            section = kwargs["section"]
            settings = request.cms.load_theme_settings()
            context["base_template"] = settings["sections"][section]["extends"]
        
        return context
    
    # themed by middleware
    def get_template_names(self):
        template = self.object.template_content.template_name
        return [template]



# the template is the sections base template
class GenericSectionHomeView(TemplateView):

    def get(self, request, *args, **kwargs):
        section = kwargs["section"]

        settings = request.cms.load_theme_settings()
        self.template_name = settings["sections"][section]["extends"]

        return self.render_to_response({})
    

# this always extends the Main section base template
class GenericHomePageView(TemplateView):

    template_name = "base.html"

    def get(self, request, *args, **kwargs):
        
        preview = self.request.GET.get("preview",False)

        # check if there is an assigned home template_content
        hp = TemplateContent.objects.filter(is_home_page=True, published_version__isnull=preview).first()

        if hp and (preview or hp.published_at != None):

            localized_hp = LocalizedTemplateContent.objects.filter(template_content=hp, language=hp.cms.primary_language()).first()
            if localized_hp:
            
                response = redirect(reverse("micromanager_page", kwargs={"slug":localized_hp.slug}))

                if preview:
                    response['Location'] += '?preview=1'
                    
                return response
        
        return self.render_to_response({})


"""
    ADMIN VIEWS
"""
class MicroManagerAdmin(AdminOnlyMixin, TemplateView):
    template_name = "micromanager/admin/base.html"


"""
    Creating a template_content consists of
    - selecting a template
    - supplying a title
    - the title is always in the current language
"""
class CreateTemplateContent(AdminOnlyMixin, FormView):

    template_name = "micromanager/admin/create_template_content.html"
    form_class = CreateTemplateContentForm

    def get_context_data(self, **kwargs):
        context = super(CreateTemplateContent, self).get_context_data(**kwargs)
        context['template_type'] = self.kwargs['template_type']
        return context

    def form_valid(self, form):
        # create a new template_content for this cms

        template_content = TemplateContent.objects.create(
            self.request.user,
            self.request.cms,
            form.cleaned_data['title'],
            form.cleaned_data['template_name'],
            self.kwargs['template_type'],
        )

        template_content.save()

        return redirect("micromanager_manage_template_content", pk=template_content.pk)

    def get_form_kwargs(self):
        kwargs = super(CreateTemplateContent, self).get_form_kwargs()
        kwargs['cms'] = self.request.cms
        kwargs['template_type'] = self.kwargs['template_type']
        return kwargs
        

"""
    Manage a Localized TemplateContent
    The template is read and the content elements the user has to fill are detected and
    presented in a form

    subclassed by ManageTheme
"""
class ManageMicroContents(AdminOnlyMixin, TemplateView):

    template_name = "micromanager/admin/manage_template_content.html"
    form_class = ManageMicroContentsForm

    def dispatch(self, request, *args, **kwargs):
        self.language = kwargs.get("language", request.cms.primary_language())
        self.template_content = kwargs.get("template_content", None)
        self.request = request
        return super(ManageMicroContents, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ManageMicroContents, self).get_context_data(**kwargs)
        context["template_content"] = self.template_content
        context["language"] = self.language
        return context


    def _save_content(self, template_content, language, field, content, user):
        if hasattr(field, "instance") and field.instance.pk:
            field.instance.set_content(content, user, language)
        else:
            instance = field.cms_object.Model.objects.create(
                    template_content,
                    language,
                    field.cms_object.content_type,
                    content,
                    user,
                )

            # a multifield cant have ONE instance
            if field.cms_object.multi == False:
                field.instance = instance
        

    def get_initial(self):
        initial = {
            "language" : self.language,
        }
        return initial
        
    def get_form(self):
        return self.form_class(self.template_content, self.language, initial=self.get_initial())

    def get_post_form(self, POST_data):
        return self.form_class(self.template_content, self.language, POST_data)


    def save_localized_template_content(self, form):
        self.localized_template_content.translation_ready = "translation-ready" in self.request.GET
        self.localized_template_content.title = form.cleaned_data["title"]
        self.localized_template_content.last_modified_by = self.request.user
        self.localized_template_content.save()


    def save_cms_fields(self, form, for_translation=False):

        language = form.cleaned_data["language"]
        
        for field_ in form:

            field = field_.field
            if hasattr(field, "cms_object"):

                data = form.cleaned_data[field_.name]
                
                if data and ( (type(data) in [str, list] and len(data) > 0) or data is not None):

                    if type(data) == list:
                        for content in data:
                            self._save_content(self.template_content, language, field, content, self.request.user)
                    else:
                        self._save_content(self.template_content, language, field, data, self.request.user)

                else:
                    if hasattr(field, "instance") and field.instance.pk:
                        if for_translation == False:
                            field.instance.delete()
                        else:
                            localized = field.instance.get_localized(language)
                            if localized:
                                localized.draft_content=None
                                localized.save()
        

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        form = self.get_post_form(request.POST)

        if form.is_valid():
            self.form_valid(form)

            # necessary but not nice
            form = self.get_form()

        context["form"] = form
        return self.render_to_response(context)
        

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context["form"] = self.get_form()
        return self.render_to_response(context)

    
class ManageTemplateContent(ManageMicroContents):

    form_class = ManageTemplateContentForm

    def dispatch(self, request, *args, **kwargs):
        
        template_content = TemplateContent.objects.get(pk=kwargs["pk"])

        language = kwargs.get("language", request.cms.primary_language())

        self.localized_template_content = LocalizedTemplateContent.objects.filter(template_content=template_content, language=language).first()

        if not self.localized_template_content:
            # maybe thje primary language has been changed
            # this requires the creatoni of the primary language
            temp_content = LocalizedTemplateContent.objects.filter(template_content=template_content).first()
            if not temp_content:
                title = _("Temporary Title")
            else:
                title = "[%s] %s" % (_("needs translation"), temp_content)
            self.localized_template_content = LocalizedTemplateContent.objects.create(request.user,
                                                        template_content, language, title)

        # pass template_content to the superclass
        kwargs["template_content"] = template_content

        return super(ManageTemplateContent, self).dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(ManageTemplateContent, self).get_context_data(**kwargs)
        context["localized_template_content"] = self.localized_template_content
        context["view_name"] = "micromanager_manage_template_content"
        context["view_arg"] = self.localized_template_content.template_content.pk
        return context


    def form_valid(self, form):
        # save the template_content
        self.save_localized_template_content(form)

        # manage home template_content
        if form.cleaned_data.get("is_home_page", False) == True:
            
            for page_ in TemplateContent.objects.filter(cms=self.template_content.cms):
                if page_.is_home_page:
                    page_.is_home_page = False
                    page_.save()

            self.template_content.is_home_page = True
            self.template_content.save()


        types = form.cleaned_data.get('page_types', [])
        for page_type in TemplateContentTypes.objects.filter(template_content=self.template_content):
            if page_type.content_type in types:
                # remove frm add_list
                types.pop(types.index(page_type.content_type))
            else:
                # delete db entry
                page_type.delete()

        for t in types:
            pt = TemplateContentTypes(
                template_content = self.template_content,
                content_type = t
            )
            pt.save()

        # save the microcontent
        self.save_cms_fields(form)


    def get_initial(self):

        is_home_page = self.localized_template_content.template_content.is_home_page
        
        initial = {
            "title" : self.localized_template_content.title,
            "language" : self.localized_template_content.language,
            "is_home_page" : is_home_page,
            "page_types" : self.localized_template_content.types(),
        }
        return initial

        
    def get_form(self):
        return self.form_class(self.template_content, self.language, initial=self.get_initial())        




"""
    above each field the source text/image needs to be shown
"""
class TranslateTemplateContent(ManageMicroContents):

    template_name = "micromanager/admin/translate_template_content.html"
    form_class = TranslatePageForm

    def dispatch(self, request, *args, **kwargs):
        template_content = TemplateContent.objects.get(pk=kwargs["pk"])
        kwargs["template_content"] = template_content

        self.language = kwargs["language"]

        # create or fetch the new localized template_content
        self.localized_template_content = LocalizedTemplateContent.objects.filter(template_content=template_content, language=self.language).first()

        if not self.localized_template_content:
            self.localized_template_content = LocalizedTemplateContent.objects.create(request.user, template_content, self.language, str(_("Translation needed")))
        
        return super(TranslateTemplateContent, self).dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(TranslateTemplateContent, self).get_context_data(**kwargs)
        context["source_page"] = LocalizedTemplateContent.objects.get(language=self.request.cms.primary_language(), template_content=self.template_content)
        return context


    def form_valid(self, form):

        localized_template_content = LocalizedTemplateContent.objects.get(template_content=self.template_content, language=form.cleaned_data["language"])
    
        # save the template_content
        self.save_localized_template_content(form)

        self.save_cms_fields(form, for_translation=True)


    def get_initial(self):
        initial = {
            "title" : self.localized_template_content.title,
            "language" : self.language,
        }
        return initial


    def get_form(self):
        return self.form_class(self.template_content, self.language, initial=self.get_initial(), for_translation=True)

    def get_post_form(self, POST_data):
        return self.form_class(self.template_content, self.language, POST_data, for_translation=True)


class PublishTemplateContent(TemplateView):

    template_name = "micromanager/admin/list_template_content_entry.html"

    def dispatch(self, request, *args, **kwargs):

        self.template_content = TemplateContent.objects.get(pk=kwargs["template_content_id"])
        self.language = kwargs.get("language", "all")

        return super(PublishTemplateContent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context["template_content"] = self.template_content
        context["publication"] = True
        context["publication_errors"] = self.template_content.publish(language=self.language)    

        return self.render_to_response(context)
            


"""
    Sections
    - there can be multile bases, like base.html or blog_base.html
"""


class ManageBase(ManageMicroContents):

    form_class = ManagePagebaseForm

    def dispatch(self, request, *args, **kwargs):
        #self.section = kwargs.pop("section_name")
        self.request = request

        # get the template and create the template_content db entry
        # theme_settings = request.cms.load_theme_settings()
        #self.template = theme_settings["sections"][self.section]["base"]

        return super(ManageBase, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ManageBase, self).get_context_data(**kwargs)
        context["view_arg"] = "global"
        context["view_name"] = "micromanager_manage_base"
        return context


    def get_form(self):
        #template_path = os.path.join(self.request.cms.get_templates_path(), self.template_name)
        t = loader.get_template("base.html")
        return self.form_class(t.template, self.language, initial=self.get_initial())  



class ManageNavigations(AdminOnlyMixin, TemplateView):

    template_name = "micromanager/admin/manage_navigation.html"

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        nav_type = request.POST["navtype"]
        
        order = request.POST.get("order", None)

        if order is not None:
            order = json.loads(order)

            for counter, template_content_id in enumerate(order, start=1):

                naventry = TemplateContentTypes.objects.get(content_type=nav_type,
                                                            template_content_id=template_content_id)
                naventry.position = counter
                naventry.save()
        
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        theme = Theme(request.cms.theme)

        sortables = {
        }
        
        for nav_class in theme.settings["navigations"]:
            pages = TemplateContentTypes.objects.filter(content_type=nav_class).order_by("position")
            sortables[nav_class] = pages

        context["navigations"] = sortables

        return self.render_to_response(context)



class TemplateContentList(AdminOnlyMixin, ListView):
    
    template_name = "micromanager/admin/list_template_content.html"
    
    model = TemplateContent

    def get_queryset(self):
        return TemplateContent.objects.filter(cms=self.request.cms, template_type=self.kwargs['template_type'])


class DeleteTemplateContent(AdminOnlyMixin, TemplateView):
    
    template_name = "micromanager/admin/delete_template_content.html"

    # post for browser "send again ?" warning
    # post data is not used
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        template_content = TemplateContent.objects.filter(pk=kwargs["template_content_id"]).first()

        if template_content:
            template_content.delete()

            
        context.update(kwargs)
        context["success"] = True

        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        return self.render_to_response(kwargs)


"""
    this deletes Textarea or TextInput fields, including CKEditor
    ajax is not used
"""
class DeleteContent(AdminOnlyMixin, TemplateView):

    template_name = 'micromanager/admin/delete_content.html'
    form_class = DeleteContentForm

    def dispatch(self, request, *args, **kwargs):
        self.kwargs = kwargs
        self.request = request
        
        self.language = kwargs['language']
        
        template_content_id = kwargs.get('template_content_id', None)
        self.template_content = None
        if page_id is not None:
            self.template_content = TemplateContent.objects.get(pk=template_content_id)
        return super(DeleteContent, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DeleteContent, self).get_context_data(**kwargs)
        context["template_content"] = self.template_content
        context["language"] = self.language
        context["view_name"] = self.__class__.__name__
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        form = self.form_class(request.POST)

        success = False

        if form.is_valid():
        
            Model = content_category_model_map[form.cleaned_data["content_category"]]
            content = Model.objects.filter(pk=form.cleaned_data["pk"]).first()

            if content:
                content.delete()

            success = True

            context["success"] = success
            self.on_success(context, form)

        context["form"] = form
        context["success"] = success
        
        return self.render_to_response(context)


    def on_success(self, context, form):
        pass


    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        initial = {
            "pk" : request.GET["pk"],
            "content_category" : request.GET["category"],
            "content_type" : request.GET.get("contenttype", None),
        }

        form = self.form_class(initial=initial)

        context.update({
            "form" : form,
        })
        
        return self.render_to_response(context)


# files are handled via ajax
class DeleteFileContent(DeleteContent):

    def on_success(self, context, form):
        
        content_category = form.cleaned_data["content_category"]
        content_type = form.cleaned_data["content_type"]

        cms_tag = CMSTag(content_category, content_type)

        widget_attrs = cms_tag._get_widget_attrs()

        field = cms_tag._create_field(self.language, widget_attrs=widget_attrs)
        fieldform = forms.Form()
        fieldform.fields[field["name"]] = field["field"]

        context["fieldform"] = fieldform
        context["form"] = form
        context["field_id"] = "id_pk-%s-%s" %(form.cleaned_data["pk"], content_type)
        
        return self.render_to_response(context)
        

"""
    ajax upload image
    - receives content_type, content_category, file, template_content_id, language, [pk]
"""
class UploadFile(AdminOnlyMixin, TemplateView):

    template_name = "micromanager/admin/filecontent_field_form.html"

    form_class = UploadFileForm

    def post(self, request, *args, **kwargs):

        content_type = kwargs["content_type"]
        content_category = kwargs["content_category"]

        language = kwargs.get("language", request.cms.primary_language())
        
        cms_tag = CMSTag(content_category, content_type)

        widget_attrs = cms_tag._get_widget_attrs()

        form = self.form_class(request.POST, request.FILES)

        # this is not nice - it should be kwargs
        template_content_id = request.POST.get('template_content_id', None)
        template_content = None
        
        if template_content_id is not None:
            template_content = TemplateContent.objects.get(pk=template_content_id)

        if form.is_valid():
            pk = form.cleaned_data.get("pk", None)
            file = form.cleaned_data["file"]
            
            language = form.cleaned_data["language"]

            Model = content_category_model_map[content_category]

            if pk is not None:
                instance = Model.objects.get(pk=form.cleaned_data["pk"])
                instance.set_content(file, request.user, language)

            else:
                instance = Model.objects.create(template_content, language, content_type, file, request.user)

            field = cms_tag._create_field(language, instance, widget_attrs=widget_attrs)

        else:
            field = cms_tag._create_field(language, widget_attrs=widget_attrs)

        fieldform = forms.Form()
        fieldform.fields[field["name"]] = field["field"]

        # fields do not render outside forms, we have to pass a form to the template

        context = {
            "fieldform" : fieldform,
            "form" : form,
            "template_content" : template_content,
            "language" : language,
        }
        
        return self.render_to_response(context)


class UploadImage(UploadFile):
    form_class = UploadImageForm


class ManageLanguages(AdminOnlyMixin, TemplateView):

    template_name = "micromanager/admin/manage_languages.html"
    form_class = AddLanguageForm
    
    def post(self, request, action, language_id=None, *args, **kwargs):
        context = super(ManageLanguages, self).get_context_data(**kwargs)

        form = self.form_class()

        if action == "setasprimary":
            new_primary = CMSLanguages.objects.get(cms=self.request.cms, pk=language_id) # for security reasons, require cms
            new_primary.is_primary = True
            new_primary.save()

        elif action == "add":

            form = self.form_class(request.POST)

            if form.is_valid():
                new_language = form.save(commit=False)
                new_language.cms = self.request.cms
                new_language.save()
        
        context["languages"] = CMSLanguages.objects.filter(cms=self.request.cms)
        context["form"] = form
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        context = super(ManageLanguages, self).get_context_data(**kwargs)
        context["languages"] = CMSLanguages.objects.filter(cms=request.cms)
        context["form"] = self.form_class()
        return self.render_to_response(context)


class DeleteLanguage(AdminOnlyMixin, TemplateView):

    template_name = "micromanager/admin/remove_language.html"

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()

        language = CMSLanguages.objects.filter(cms=self.request.cms, pk=kwargs["language_id"]).first()

        if language:
            language.delete()

        context["success"] = True
        context["language_id"] = kwargs["language_id"]
        return self.render_to_response(context)
        

    def get(self, request, *args, **kwargs):
        return self.render_to_response(kwargs)


class ThemeSettings(AdminOnlyMixin, FormView):

    template_name = "micromanager/admin/set_theme.html"
    form_class = ThemeSettingsForm

    def form_valid(self, form):
        context = self.get_context_data()

        theme = form.cleaned_data["theme"]

        if self.request.cms.theme != theme:
            self.request.cms.theme = theme
            self.request.cms.save()

        context["form"] = form
        context["success"] = True

        return self.render_to_response(context)


class FirstTimeSetup(FormView):

    template_name = 'micromanager/setup_cms.html'
    form_class = FirstTimeSetupForm

    def dispatch(self, request, *args, **kwargs):
        if CMS.objects.all().exists():
            return redirect(reverse('micromanager_home'))
        return super(FirstTimeSetup, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cms = CMS.objects.create(form.cleaned_data['cms_name'], form.cleaned_data['theme'],
                                 form.cleaned_data['primary_language'])

        return redirect(reverse('micromanager_home'))

class CreateAdminAccount(FormView):

    template_name = 'micromanager/setup_admin_account.html'
    form_class = CreateAdminForm

    def dispatch(self, request, *args, **kwargs):
        if User.objects.filter(is_superuser=True).exists():
            return redirect(reverse('micromanager_home'))
        return super(CreateAdminAccount, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        admin = form.save()
        return redirect(reverse('micromanager_home'))
