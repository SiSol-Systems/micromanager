from django.conf import settings
from django import template
register = template.Library()

from django.template import loader, Context

from micromanager.models import (TemplateContent, LocalizedTemplateContent, MicroContent, ContentImages, content_category_model_map,
                              TemplateContentTypes)

from django.db.models import Q

"""
    tags for templated contents, fetch by TemplateContentType
"""
@register.assignment_tag(takes_context=True)
def get_content_by_type(context, content_type, *args, **kwargs):
    cms = context["request"].cms
    language = context["request"].cms_language

    limit = kwargs.get('limit', None)

    preview = "preview" in context["request"].GET
    template_content_ids = TemplateContentTypes.objects.filter(template_content__cms=cms, content_type=content_type,
                                                               template_content__published_at__isnull=preview).order_by("position").values_list("template_content_id", flat=True)

    if limit is not None:
        template_content_ids = template_content_ids[:limit]

    template_content_ids = list(template_content_ids)
    # does not preserve order
    localized_tcs = LocalizedTemplateContent.objects.filter(template_content_id__in=template_content_ids, language=language)

    localized_tcs = list(localized_tcs)
    localized_tcs.sort(key=lambda localized_tc: template_content_ids.index(localized_tc.template_content.id))

    return localized_tcs

"""
    returns all pages of a given type
"""
@register.assignment_tag
def get_template_content_locale(template_content, language):
    return LocalizedTemplateContent.objects.filter(template_content=template_content, language=language).first()

"""
    fetch_by_template_name
"""
@register.assignment_tag(takes_context=True)
def get_template_content(context, template_name, *args, **kwargs):
    cms = context["request"].cms
    language = context["request"].cms_language
    limit = kwargs.get('limit', None)

    preview = "preview" in context["request"].GET
    template_content_ids = TemplateContent.objects.filter(cms=cms, template_name=template_name,
                                                          published_at__isnull=preview).order_by("-published_at").values_list("id", flat=True)

    if limit is not None:
        template_content_ids = template_content_ids[:limit]

    template_content_ids = list(template_content_ids)
    # does not preserve order
    localized_tcs = LocalizedTemplateContent.objects.filter(template_content_id__in=template_content_ids, language=language)

    localized_tcs = list(localized_tcs)
    localized_tcs.sort(key=lambda localized_tc: template_content_ids.index(localized_tc.template_content.id))

    return localized_tcs

"""
    common tag for microcontent(images and html)
"""

@register.assignment_tag(takes_context=True)
def cms_getall(context, content_category, content_type, *args, **kwargs):

    template_content = context['template_content']

    Model = content_category_model_map[content_category]
    microcontent = Model.objects.filter(template_content=template_content)

    dic = {}
    dic[content_type] = microcontent
    
    return dic
    

"""
    returns a single micro content
    does not support template_content
    needs "template_content" in context
"""
# helper
def cms_get(context, content_category, content_type, *args, **kwargs):

    template_content = context.get("template_content", None)

    preview = "preview" in context["request"].GET
    
    Model = content_category_model_map[content_category]

    microcontent = Model.objects.filter(Q(template_content=template_content, content_type=content_type) | Q(template_content__isnull=True, content_type=content_type)).first()
        
    if microcontent:
        if microcontent.template_content == None:
            preview = True
        microcontent = microcontent.get_content(context["request"].cms_language, preview)

    return microcontent


'''
    template_content or microcontent?
'''
@register.assignment_tag(takes_context=True)
def cms_get_multiple(context, content_category, content_type, *args, **kwargs):

    template_content = context['template_content']

    Model = content_category_model_map[content_category]
    instances = Model.objects.filter(template_content=template_content, content_type=content_type)

    content = []

    for instance in instances:
        content.append(instance.get_content(context["request"].cms_language))

    return content


"""
    shortcuts for getting MicroContent
"""
@register.simple_tag(takes_context=True)
def cms_get_microcontent(context, content_type, *args, **kwargs):
    html = cms_get(context, "microcontent", content_type, *args, **kwargs)
    return html


@register.assignment_tag(takes_context=True)
def cms_get_microcontents(context, content_type, *args, **kwargs):
    html = cms_get_multiple(context, "microcontent", content_type, *args, **kwargs)
    return html


@register.assignment_tag(takes_context=True)
def cms_get_image(context, content_type, *args, **kwargs):
    image = cms_get(context, "image", content_type, *args, **kwargs)
    return image

"""
    multiple images
"""
@register.assignment_tag(takes_context=True)
def cms_get_images(context, content_type, *args, **kwargs):
    image = cms_get_multiple(context, "image", content_type, *args, **kwargs)
    return image


@register.filter
def template_content_translation_complete(template_content, language):
    ltc = template_content.get_localized(language)

    if not ltc:
        return False

    else:
        return ltc.translation_complete()


@register.assignment_tag(takes_context=True)
def get_sections(context, *args, **kwargs):
    settings = context["request"].cms.load_theme_settings()

    sections = []
    
    for section, dic in settings["sections"].items():
        sections.append(section)
    return sections

@register.assignment_tag
def get_localized_microcontent(instance, language):
    return instance.get_content(language)


@register.simple_tag
def get_localized_attribute(template_content, language, attr):

    lp = LocalizedTemplateContent.objects.get(template_content=template_content, language=language)

    return getattr(lp, attr)


'''
    by default fetches latest db entry
    make this configurable
'''
@register.simple_tag(takes_context=True)
def include_latest_content(context, template_name):
    t = loader.get_template(template_name)

    # create the correct context
    template_content = TemplateContent.objects.filter(template_name=template_name).last()
    template_context = Context({
        'request': context['request'],
        'template_content': template_content,
        'localized_template_content' : template_content.get_localized(context['request'].cms.get_language()),
    })
    return t.render(template_context)


@register.simple_tag(takes_context=True)
def include_content(context, localized_template_content):
    t = loader.get_template(localized_template_content.template_content.template_name)

    # create the correct context
    template_context = Context({
        'request': context['request'],
        'template_content': localized_template_content.template_content,
        'localized_template_content' : localized_template_content,
    })
    return t.render(template_context)

'''
    bootstrap
'''
@register.inclusion_tag('micromanager/bootstrap_form.html')
def render_bootstrap_form(form):
    return {'form':form}
