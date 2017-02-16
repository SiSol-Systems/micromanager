from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
import threading
try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse
from django.shortcuts import redirect

from micromanager.models import INSTALLED_THEMES, CMS

from django.contrib.auth import get_user_model
User = get_user_model()

DEFAULT_THEME = INSTALLED_THEMES[0][0]
MULTI_TENANCY = getattr(settings, "MICROMANAGER_MULTI_TENANCY", False)


_thread_local = threading.local()


class MiddlewareMixin(object):
    def __init__(self, get_response=None):
        self.get_response = get_response
        super(MiddlewareMixin, self).__init__()

    def __call__(self, request):
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        if not response:
            response = self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response


"""
    Add request.cms
"""
class MicroManagerMiddleware(MiddlewareMixin):

    def process_request(self, request):

        if 'micromanager-setup' in request.path:
            return None

        if not User.objects.filter(is_superuser=True).exists():
            return redirect(reverse('micromanager_create_admin'))

        if not hasattr(request, "cms") or request.cms is None:
        
            if MULTI_TENANCY == True:
                raise ValueError("Multi Tenancy not supported yet")

            else:
                cms = CMS.objects.all().first()

                if not cms:
                    return redirect(reverse('micromanager_setup'))
                    
            request.cms = cms

        request.cms_language = request.cms.get_language()

        return None
        



def get_current_theme():
    theme = getattr(_thread_local, 'theme', DEFAULT_THEME)
    return theme


class ThemeMiddleware(MiddlewareMixin):

    # make request available for template loader
    def process_request(self, request):
        # cms is attached to request in observatories.middleware
        cms = getattr(request, "cms", None)
        if cms is not None:
            theme = cms.theme
            _thread_local.theme = theme
        return None
