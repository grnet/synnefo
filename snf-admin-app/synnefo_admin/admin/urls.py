from django.conf.urls import patterns, url

urlpatterns = patterns('synnefo_admin.admin.views',
    url(r'^$', 'index', name='admin-index'),
    url(r'^actions/vm-suspend/(?P<vm_id>[0-9]+)$', 'vm_suspend',
        name='admin-suspend-vm'),
    url(r'^actions/vm-suspend-release/(?P<vm_id>[0-9]+)$',
        'vm_suspend_release', name='admin-suspend-vm-release'),
    url(r'^actions/vm-shutdown/(?P<vm_id>[0-9]+)$', 'vm_shutdown',
        name='admin-vm-shutdown'),
    url(r'^actions/vm-start/(?P<vm_id>[0-9]+)$', 'vm_start',
        name='admin-vm-start'),
    url(r'^(?P<search_query>.*)$', 'account',
        name='admin-details'),
)
