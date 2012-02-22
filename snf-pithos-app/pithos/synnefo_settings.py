"""
Hooks for snf-webproject used in snf-pithos-app setup.py entry_points
"""

from django.conf.urls.defaults import include, patterns

synnefo_installed_apps = ['pithos.api']
synnefo_urls = patterns('',
    (r'', include('pithos.urls')),
)
synnefo_middlewares = [
    'pithos.middleware.LoggingConfigMiddleware',
    'pithos.middleware.SecureMiddleware'
]

from pithos.api.synnefo_settings import *
