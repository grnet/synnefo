
from distutils.core import setup

setup   (
    name            =   'commissioning',
    version         =   '0.3',
    packages        =   [
            'commissioning',
            'commissioning.lib',
            'commissioning.lib.django_server',
            'commissioning.lib.django_server.server_app',
            'commissioning.lib.kamaki',
            'commissioning.utils',
    ]
)
