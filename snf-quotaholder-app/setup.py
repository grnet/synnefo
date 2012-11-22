
from distutils.core import setup

setup   (
    name            =   'quotaholder_django',
    version         =   '0.5',
    packages        =   [
            'quotaholder_django',
            'quotaholder_django.quotaholder_app',
    ],

    package_data    =   {
            'quotaholder_django.quotaholder_app': ['fixtures/*.json']
    },

    scripts         =   [
            'quotaholder_django/quotaholder-manage',
    ]
)
