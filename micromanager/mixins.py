from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from micromanager.models import CMS
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

def import_class(cl):
    d = cl.rfind(".")
    classname = cl[d+1:len(cl)]
    m = __import__(cl[0:d], globals(), locals(), [classname])
    return getattr(m, classname)

'''
    SINGLE CMS: use mixins to get cms from db
    MULTI CMS: uses middleware - attached to request
'''
class AdminOnlyMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        if request.user.is_authenticated() and (request.user.is_staff or request.user.is_superuser):        
            return super(AdminOnlyMixin, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

        return super(AdminOnlyMixin, self).dispatch(request, *args, **kwargs)
    
    
if hasattr(settings, "MICROMANAGER_ADMIN_ONLY_MIXIN"):
    AdminOnlyMixin = import_class(settings.MICROMANAGER_ADMIN_ONLY_MIXIN)


"""
class CMSContentProtectorMixin(object):

    def dispatch(self, request, *args, **kwargs):
        # self.cms is assigned
        # check content obj cms
        if "localized_content_id" in kwargs:
            content = LocalizedStaticContent.objects.filter(pk=kwargs["localized_content_id"]).first()
            if content:
                if content.content.cms != self.cms:
                    raise PermissionDenied
            else:
                raise ObjectDoesNotExist("This object does not exist")
        elif "content_id" in kwargs:
            content = StaticContent.objects.filter(pk=kwargs["content_id"]).first()
            if content:
                if content.cms != self.cms:
                    raise PermissionDenied
            else:
                raise ObjectDoesNotExist("This object does not exist")
            
        return super(CMSContentProtectorMixin, self).dispatch(request, *args, **kwargs)


    def get_object(self, queryset=None):
        obj = super(CMSContentProtectorMixin, self).get_object(queryset)

        if type(obj) == StaticContent:
            if self.cms != obj.cms:
                raise PermissionDenied

        elif type(obj) == LocalizedStaticContent:
            if self.cms != obj.content.cms:
                raise PermissionDenied

        else:
            raise PermissionDenied

        return obj
"""
