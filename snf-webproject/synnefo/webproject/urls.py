# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import os

from django.conf.urls.defaults import *
from synnefo.util.entry_points import extend_urls
from django.utils.importlib import import_module
from django.conf import settings

urlpatterns = patterns('')

ROOT_REDIRECT = getattr(settings, 'WEBPROJECT_ROOT_REDIRECT', None)
if ROOT_REDIRECT:
    urlpatterns += patterns('django.views.generic.simple',
                            url(r'^$', 'redirect_to', {'url': ROOT_REDIRECT}))

urlpatterns += patterns('',
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
            urlpatterns += patterns('', url(url_r,
                 'django.views.static.serve',
                 {'document_root': static_root,
                  'show_indexes': getattr(settings,
                      'WEBPROJECT_STATIC_SHOW_INDEXES', True)}))

        else:
            # app contains static files in <appname>/static/<appname>
            for fpath in os.listdir(static_root):
                urlns = ns + fpath
                url_r = r'^%s%s/(?P<path>.*)$' % (settings.MEDIA_URL.lstrip("/"), urlns)
                static_root = os.path.join(static_root, urlns)
                urlpatterns += patterns('',  url(url_r,
                     'django.views.static.serve',
                     {'document_root': static_root,
                      'show_indexes': getattr(settings,
                          'WEBPROJECT_STATIC_SHOW_INDEXES', True)}))

    # also serve the media root after all explicitly defined paths
    # to be able to serve uploaded files
    urlpatterns += patterns('', url(r'^%s(?P<path>.*)$' % \
         settings.MEDIA_URL.lstrip("/"),
         'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT,
          'show_indexes': getattr(settings,
              'WEBPROJECT_STATIC_SHOW_INDEXES', True)}))



urlpatterns = extend_urls(urlpatterns, 'synnefo')

