"""
Hooks for snf-webproject used in snf-pithos-app setup.py entry_points
"""

from django.conf.urls.defaults import include, patterns

synnefo_installed_apps = ['pithos.ui', 'pithos.api']
synnefo_urls = patterns('',
    (r'^pithos', include('pithos.urls')),
)
synnefo_middlewares = [
    'pithos.middleware.LoggingConfigMiddleware',
    'pithos.middleware.SecureMiddleware',
    'pithos.middleware.UserMiddleware'
]
