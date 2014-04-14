# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os


# Import * in order to import the http exception handlers: handler*
try:
    from django.conf.urls.defaults import *
except ImportError:  # Django==1.4
    from django.conf.urls import *

from synnefo.util.entry_points import extend_urls
from django.utils.importlib import import_module
from django.template import Context, loader, RequestContext
from django import http
from django.conf import settings

urlpatterns = patterns('')

ROOT_REDIRECT = getattr(settings, 'WEBPROJECT_ROOT_REDIRECT', None)
if ROOT_REDIRECT:
    urlpatterns += patterns('django.views.generic.simple',
                            url(r'^$', 'redirect_to', {'url': ROOT_REDIRECT}))

urlpatterns += patterns(
    '',
    (r'^lang/$', 'synnefo.webproject.i18n.set_language')
)

if getattr(settings, 'WEBPROJECT_SERVE_STATIC', settings.DEBUG):

    for module_name, ns in settings.STATIC_FILES.iteritems():
        module = import_module(module_name)
        app_dir = 'static'

        # hook defined that application contains media files in other than
        # ``static`` directory
        # (e.g. django.contrib.admin which contains media files in media dir)
        if type(ns) == tuple:
            app_dir = ns[0]
            ns = ns[1]

        static_root = os.path.join(os.path.dirname(module.__file__), app_dir)
        if ns:
            # app contains static files in <appname>/static/
            urlns = ns
            url_r = r'^%s%s/(?P<path>.*)$' % (settings.MEDIA_URL.lstrip("/"),
                                              urlns)
            urlpatterns += patterns(
                '', url(url_r,
                        'django.views.static.serve',
                        {'document_root': static_root,
                         'show_indexes': getattr(
                             settings, 'WEBPROJECT_STATIC_SHOW_INDEXES', True)
                         }))

        else:
            # app contains static files in <appname>/static/<appname>
            for fpath in os.listdir(static_root):
                urlns = ns + fpath
                url_r = r'^%s%s/(?P<path>.*)$' % \
                    (settings.MEDIA_URL.lstrip("/"), urlns)
                static_root = os.path.join(static_root, urlns)
                urlpatterns += patterns(
                    '',  url(url_r,
                             'django.views.static.serve',
                             {'document_root': static_root,
                              'show_indexes': getattr(
                                  settings,
                                  'WEBPROJECT_STATIC_SHOW_INDEXES', True)
                              }))

    # also serve the media root after all explicitly defined paths
    # to be able to serve uploaded files
    urlpatterns += patterns(
        '', url(r'^%s(?P<path>.*)$' %
                settings.MEDIA_URL.lstrip("/"),
                'django.views.static.serve',
                {'document_root': settings.MEDIA_ROOT,
                 'show_indexes': getattr(
                     settings, 'WEBPROJECT_STATIC_SHOW_INDEXES', True)
                 }))

urlpatterns = extend_urls(urlpatterns, 'synnefo')


def handle500(request, template_name="500.html"):
    t = loader.get_template(template_name)
    context = Context({})
    try:
        context = RequestContext(request)
    except:
        pass
    return http.HttpResponseServerError(t.render(context))

handler500 = handle500
