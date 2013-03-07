from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'synnefo.helpdesk.views.index', name='helpdesk-index'),
    url(r'^suspend/(?P<vm_id>[0-9]+)$', 'synnefo.helpdesk.views.suspend_vm',
        name='helpdesk-suspend-vm'),
    url(r'^suspend_release/(?P<vm_id>[0-9]+)$',
        'synnefo.helpdesk.views.suspend_vm_release',
        name='helpdesk-suspend-vm-release'),
    url(r'^(?P<account_or_ip>.*)$', 'synnefo.helpdesk.views.account',
        name='helpdesk-details'),
)

