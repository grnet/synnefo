from django.conf.urls.defaults import *
from views import quotaholder_0_2

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^quota/', include('quota.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    (r'^0.2/(?P<call_name>[_A-Za-z0-9]*)', quotaholder_0_2),
)
