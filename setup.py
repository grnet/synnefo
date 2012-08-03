
from distutils.core import setup

setup   (
    name        =   'commissioning',
    version     =   '0.3',
    packages    =   [
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
                        'commissioning.servers.quotaholder_django',
                        'commissioning.servers.quotaholder_django.django_backend',
			'commissioning.servers.fscrud',

                        'commissioning.utils',
                    ],

    scripts     =   [
                        'commissioning/servers/quotaholder_django/quotaholder-manage',
                        'commissioning/servers/fscrud/fscrud-manage',
                    ]
)
