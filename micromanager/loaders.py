from django.template.loaders.base import Loader as BaseLoader
from django.core.exceptions import SuspiciousFileOperation
from django.utils._os import safe_join
from django.template import TemplateDoesNotExist
import os, io

from micromanager.middleware import get_current_theme

class ThemeLoader(BaseLoader):
    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):        
        """
        An iterator that yields possible matching template paths for a
        template name.
        """        
        theme = get_current_theme()
        template_dir = os.path.join(os.path.dirname(__file__), "themes", theme, "templates")

        if os.path.isdir(template_dir):
            try:
                yield safe_join(template_dir, template_name)
            except SuspiciousFileOperation:
                pass
        

    def load_template_source(self, template_name, template_dirs=None):
        for filepath in self.get_template_sources(template_name, template_dirs):
            try:
                with io.open(filepath, encoding=self.engine.file_charset) as fp:
                    return fp.read(), filepath
            except IOError:
                pass
        raise TemplateDoesNotExist(template_name)
        
