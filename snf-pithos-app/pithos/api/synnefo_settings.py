"""
Hooks for snf-webproject used in snf-pithos-app setup.py entry_points
"""

synnefo_installed_apps = ['pithos.api']

# apply required middleware
synnefo_middlewares = [
    'synnefo.lib.middleware.LoggingConfigMiddleware',
    'synnefo.lib.middleware.SecureMiddleware'
]
