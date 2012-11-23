from django.conf.urls.defaults import *
from django.conf import settings
from views import view

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

app_ex = '(?P<appname>[^/]*)'
ver_ex = '(?P<version>[^/]*)'
call_ex = '(?P<callname>[_A-Za-z0-9]*)'
#generic_pattern = (r'^%s/%s/%s' % (app_ex, ver_ex, call_ex), generic_view)


pats = [(r'%s/%s/%s' % (app_ex, ver_ex, call_ex), view)]
                                                

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),

    *pats
)
