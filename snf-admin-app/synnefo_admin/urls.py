from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    '',
    url(r'^admin/', include('synnefo_admin.admin.urls')),
    url(r'^stats/', include('synnefo_admin.stats.urls')),
)

