from synnefo.webproject.settings.default import *

from synnefo.util.entry_points import extend_list_from_entry_point, \
        extend_dict_from_entry_point

INSTALLED_APPS = extend_list_from_entry_point(INSTALLED_APPS, 'synnefo', \
        'web_apps')
MIDDLEWARE_CLASSES = extend_list_from_entry_point(MIDDLEWARE_CLASSES, \
        'synnefo', 'web_middleware')
STATIC_FILES = extend_dict_from_entry_point(STATIC_FILES, 'synnefo', \
        'web_static')
