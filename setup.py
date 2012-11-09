
from distutils.core import setup

setup   (
    name            =   'commissioning',
    version         =   '0.3',
    packages        =   [
            'commissioning',
            'commissioning.api',
            'commissioning.controllers',
            'commissioning.controllers.django_controller',

            'commissioning.specs',
            'commissioning.physicals',
            'commissioning.physicals.fscrud',

            'commissioning.clients',
            'commissioning.servers',
            'commissioning.servers.django_server',
            'commissioning.servers.django_server.server_app',
            'commissioning.servers.quotaholder',
            'commissioning.servers.quotaholder.quotaholder_django',
            'commissioning.servers.quotaholder.django_backend',
            'commissioning.servers.fscrud',
            'commissioning.servers.fscrud.fscrud_django',

            'commissioning.utils',
            'commissioning.hlapi'
    ],

    package_data    =   {
            'commissioning.servers.quotaholder.django_backend': ['fixtures/*.json']
    },

    scripts         =   [
            'commissioning/servers/quotaholder/quotaholder_django/quotaholder-manage',
            'commissioning/clients/quotaholder',
            'commissioning/servers/fscrud/fscrud_django/fscrud-manage',
    ]
)
