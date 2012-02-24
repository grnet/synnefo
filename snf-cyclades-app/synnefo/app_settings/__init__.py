synnefo_web_apps = [
    'synnefo.admin',
    'synnefo.api',
    'synnefo.ui',
    'synnefo.db',
    'synnefo.logic',
    'synnefo.plankton',
    'synnefo.ui.userdata',
]

synnefo_web_middleware = [
    {'after': 'django.middleware.locale.LocaleMiddleware', 'insert': [
        'synnefo.api.middleware.ApiAuthMiddleware'
        ]
    }
]

synnefo_static_files = {
    'synnefo.ui': 'ui',
    'synnefo.admin': 'admin',
}
