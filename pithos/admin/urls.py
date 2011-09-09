from django.conf.urls.defaults import patterns

from pithos import settings


urlpatterns = patterns('pithos.admin.views',
    (r'^/?$', 'index'),
    
    (r'^/users/?$', 'users_list'),
    (r'^/users/(\d+)/?$', 'users_info'),
    (r'^/users/create$', 'users_create'),
    (r'^/users/(\d+)/modify/?$', 'users_modify'),
    (r'^/users/(\d+)/delete/?$', 'users_delete'),
)

urlpatterns += patterns('',
    (r'^/static/(?P<path>.*)$', 'django.views.static.serve', {
                    'document_root': settings.PROJECT_PATH + '/admin/static'}))
