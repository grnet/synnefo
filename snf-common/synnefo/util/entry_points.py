import sys
import pkg_resources
import inspect


def get_entry_ponts(ns, name):
    for entry_point in pkg_resources.iter_entry_points(group=ns):
        if entry_point.name == name:
            yield entry_point


def extend_settings(ns, module_name):
    """
    Extend module from entry_point hooks
    """
    settings = sys.modules[module_name]
    # apps hook
    app_entry_points = get_entry_ponts(ns, 'apps')
    # settings hook
    settings_entry_points = get_entry_ponts(ns, 'settings')

    # extend INSTALLED_APPS setting
    NEW_INSTALLED_APPS = list(getattr(settings, 'INSTALLED_APPS', []));

    # if failed to execute app hook as function parse it as string
    # synnefo.app:get_additional_apps or app1,app2,app3
    for e in app_entry_points:
        try:
            NEW_INSTALLED_APPS = list(e.load()())
        except Exception, ex:
            NEW_INSTALLED_APPS = NEW_INSTALLED_APPS + \
                    e.module_name.split(",")

    # extend additional settings
    # TODO: existing settings logic ??
    for e in settings_entry_points:
        module = e.load()
        for k in dir(module):
            if k == k.upper():
                setattr(settings, k, getattr(module, k))

    setattr(settings, 'INSTALLED_APPS', NEW_INSTALLED_APPS)

