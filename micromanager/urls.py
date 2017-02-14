from django.conf.urls import url

from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    url(r'^$', views.GenericHomePageView.as_view(), name='micromanager_home'),
    url(r'^section/(?P<section>[-\w]+)/$', views.GenericSectionHomeView.as_view(),
        name='micromanager_section'),
    url(r'^section/(?P<section>[-\w]+)/(?P<slug>[-\w]+)/', views.GenericPageView.as_view(),
        name='micromanager_section_page'),
    url(r'^pages/(?P<pk>[\d]+)/', views.GenericPageView.as_view(), name='micromanager_page_pk'),
    url(r'^pages/(?P<slug>[-\w]+)/', views.GenericPageView.as_view(), name='micromanager_page'),
    url(r'^cms-admin/$', login_required(views.MicroManagerAdmin.as_view()), name='micromanager_admin'),
    url(r'^cms-admin/translate-page/(?P<pk>[\d]+)/(?P<language>[\w]+)/$',
        login_required(views.TranslateTemplateContent.as_view()), name='micromanager_translate_template_content'),
    url(r'^cms-admin/delete-content/(?P<template_content_id>[\d]+)/(?P<language>[\w]+)/$',
        login_required(views.DeleteContent.as_view()), name='DeleteContent'),
    url(r'^cms-admin/delete-filecontent/(?P<page_id>[\d]+)/(?P<language>[\w]+)/$',
        login_required(views.DeleteFileContent.as_view()), name='DeleteFileContent'),
    # create and manage pages and content
    url(r'^cms-admin/create-content/(?P<template_type>[\w]+)/$',
        login_required(views.CreateTemplateContent.as_view()), name='micromanager_create_template_content'),
    url(r'^cms-admin/manage-content/(?P<pk>[\d]+)/$', login_required(views.ManageTemplateContent.as_view()),
        name='micromanager_manage_template_content'),
    url(r'^cms-admin/publish-content/(?P<template_content_id>[\d]+)/$',
        login_required(views.PublishTemplateContent.as_view()), name='micromanager_publish_template_content'),
    # list template_content by template_type: 'pages' or 'content'
    url(r'^cms-admin/content/(?P<template_type>[\w]+)/$', login_required(views.TemplateContentList.as_view()),
        name='micromanager_list_template_content'),
    # delete template_content
    url(r'^cms-admin/delete-page/(?P<template_content_id>[\d]+)/$',
        login_required(views.DeleteTemplateContent.as_view()), name='micromanager_delete_template_content'),
    # for global content there is no page_id
    url(r'^cms-admin/delete-content/(?P<language>[\w]+)/$', login_required(views.DeleteContent.as_view()),
        name='DeleteContent'),
    url(r'^cms-admin/delete-filecontent/(?P<language>[\w]+)/$', login_required(views.DeleteFileContent.as_view()),
        name='DeleteFileContent'),
    url(r'^cms-admin/upload-image/(?P<content_category>[-\_\w]+)/(?P<content_type>[-\_\w]+)/$',
        login_required(views.UploadImage.as_view()), name='upload_image'),
    url(r'^cms-admin/manage-cms/$', login_required(views.ThemeSettings.as_view()),
        name='micromanager_theme_settings'),
    url(r'^cms-admin/manage-languages/$', login_required(views.ManageLanguages.as_view()),
        name='micromanager_manage_languages'),
    url(r'^cms-admin/manage-languages/(\w+)/$', login_required(views.ManageLanguages.as_view()),
        name='micromanager_manage_languages'),
    url(r'^cms-admin/manage-languages/(\w+)/(\w+)/$', login_required(views.ManageLanguages.as_view()),
        name='micromanager_manage_languages'),
    url(r'^cms-admin/remove-language/(?P<language_id>[\d]+)/$', login_required(views.DeleteLanguage.as_view()),
        name='micromanager_delete_language'),
    url(r'^cms-admin/manage-general/(\w+)/$', login_required(views.ManageBase.as_view()),
        name='micromanager_manage_base'),
    url(r'^cms-admin/manage-navigation/$', login_required(views.ManageNavigations.as_view()),
        name='micromanager_manage_navigations'),
    url(r'^micromanager-setup/cms/$', views.FirstTimeSetup.as_view(), name='micromanager_setup'),
    url(r'^micromanager-setup/admin/$', views.CreateAdminAccount.as_view(), name='micromanager_create_admin'),
]
