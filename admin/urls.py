from django.conf.urls.defaults import patterns

from synnefo import settings


urlpatterns = patterns('synnefo.admin.views',
    (r'^/?$', 'index'),
    (r'^/flavors/?$', 'flavors_list'),
    (r'^/flavors/create/?$', 'flavors_create'),
    (r'^/flavors/(\d+)/?$', 'flavors_info'),
    (r'^/flavors/(\d+)/modify/?$', 'flavors_modify'),
    (r'^/flavors/(\d+)/delete/?$', 'flavors_delete'),
    
    (r'^/images/?$', 'images_list'),
    (r'^/images/register/?$', 'images_register'),
    (r'^/images/(\d+)/?$', 'images_info'),
    (r'^/images/(\d+)/modify/?$', 'images_modify'),

    (r'^/servers/?$', 'servers_list'),

    (r'^/users/?$', 'users_list'),
    (r'^/users/invite/?$', 'users_invite'),
    (r'^/users/(\d+)/?$', 'users_info'),
    (r'^/users/(\d+)/modify/?$', 'users_modify'),
    (r'^/users/(\d+)/delete/?$', 'users_delete'),

    (r'^/invitations/?$', 'invitations_list'),
    (r'^/invitations/(\d+)/resend/?$', 'invitations_resend'),
)

urlpatterns += patterns('',
    (r'^/static/(?P<path>.*)$', 'django.views.static.serve', {
                    'document_root': settings.PROJECT_PATH + '/admin/static'}))
