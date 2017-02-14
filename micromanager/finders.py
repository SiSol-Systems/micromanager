from django.contrib.staticfiles.finders import BaseFinder, AppDirectoriesFinder
from django.core.files.storage import FileSystemStorage
from django.contrib.staticfiles import utils

from django.apps import apps

import os
from collections import OrderedDict

from micromanager.middleware import get_current_theme

searched_locations = []

'''
    Subclass of AppDirectoriesFinder searching themes static folders instead of
    apps static folders
    Only search the currently active theme
'''
class ThemeDirectoriesFinder(BaseFinder):
    storage_class = FileSystemStorage
    source_dir = 'static'

    def __init__(self, *args, **kwargs):
        
        self.theme = get_current_theme()
        # Mapping of theme folder names to storage instances
        self.storage = None

        if self.theme is not None:

            app_config = apps.get_app_config('micromanager')

            theme_path = os.path.join(app_config.path, 'themes', self.theme)
            
            theme_storage = self.storage_class(
                os.path.join(theme_path, self.source_dir))
                
            if os.path.isdir(theme_storage.location):
                self.storage = theme_storage

        super(ThemeDirectoriesFinder, self).__init__(*args, **kwargs)


    def list(self, ignore_patterns):
        """
        List all files in all app storages.
        """
        if self.storage.exists(''):  # check if storage location exists
            for path in utils.get_files(self.storage, ignore_patterns):
                yield path, self.storage


    def find(self, path, all=False):
        """
        Looks for files in the app directories.
        """
        matches = []
            
        theme_location = self.storage.location
        if theme_location not in searched_locations:
            searched_locations.append(theme_location)
        match = self.find_in_theme(path)
        if match:
            if not all:
                return match
            matches.append(match)
        return matches

    def find_in_theme(self, path):
        """
        Find a requested static file in an app's static locations.
        """
        if self.storage is not None:
            # only try to find a file if the source dir actually exists
            if self.storage.exists(path):
                matched_path = self.storage.path(path)
                if matched_path:
                    return matched_path
