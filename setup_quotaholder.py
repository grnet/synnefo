
from distutils.core import setup

setup   (
    name            =   'quotaholder',
    version         =   '0.3',
    packages        =   [
            'quotaholder',
            'quotaholder.api',
            'quotaholder.clients',
            'quotaholder.clients.kamaki',
            'quotaholder.servers',
            'quotaholder.servers.django_backend',
            'quotaholder.servers.quotaholder_django',
    ],

    package_data    =   {
            'quotaholder.servers.django_backend': ['fixtures/*.json']
    },

    scripts         =   [
            'quotaholder/servers/quotaholder_django/quotaholder-manage',
            'quotaholder/clients/quotaholder_http',
    ]
)
