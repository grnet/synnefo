# code shared from django-command-extensions
# http://code.google.com/p/django-command-extensions/

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import color
from django.utils import termcolors


def color_style():
    style = color.color_style()
    if color.supports_color():
        style.URL = termcolors.make_style(fg='green', opts=('bold',))
        style.MODULE = termcolors.make_style(fg='yellow')
        style.MODULE_NAME = termcolors.make_style(opts=('bold',))
        style.URL_NAME = termcolors.make_style(fg='red')
    return style

try:
    # 2008-05-30 admindocs found in newforms-admin brand
    from django.contrib.admindocs.views import extract_views_from_urlpatterns, simplify_regex
except ImportError:
    # fall back to trunk, pre-NFA merge
    from django.contrib.admin.views.doc import extract_views_from_urlpatterns, simplify_regex

class Command(BaseCommand):
    help = "Displays all of the url matching routes for the project."

    requires_model_validation = True

    def handle(self, *args, **options):
        if args:
            appname, = args

        style = color_style()

        if settings.ADMIN_FOR:
            settings_modules = [__import__(m, {}, {}, ['']) for m in settings.ADMIN_FOR]
        else:
            settings_modules = [settings]

        views = []
        for settings_mod in settings_modules:
            try:
                urlconf = __import__(settings_mod.ROOT_URLCONF, {}, {}, [''])
            except Exception, e:
                if options.get('traceback', None):
                    import traceback
                    traceback.print_exc()
                print style.ERROR("Error occurred while trying to load %s: %s" % (settings_mod.ROOT_URLCONF, str(e)))
                continue
            view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
            for (func, regex) in view_functions:
                func_name = hasattr(func, '__name__') and func.__name__ or repr(func)
                views.append("%(url)s\t%(module)s.%(name)s" % {'name': style.MODULE_NAME(func_name),
                                       'module': style.MODULE(func.__module__),
                                       'url': style.URL(simplify_regex(regex))})

        return "\n".join([v for v in views])
