from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'synnefo.helpdesk.views.index', name='helpdesk-index'),
    url(r'^api/users', 'synnefo.helpdesk.views.user_list',
        name='helpdesk-userslist'),
    url(r'^(?P<account_or_ip>.*)$', 'synnefo.helpdesk.views.account',
        name='helpdesk-details'),
)

