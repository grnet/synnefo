synnefo_web_apps = [
    'synnefo.aai',
    'synnefo.admin',
    'synnefo.api',
    'synnefo.ui',
    'synnefo.db',
    'synnefo.logic',
    'synnefo.invitations',
    'synnefo.helpdesk',
    'synnefo.plankton',
    'synnefo.ui.userdata',
]

synnefo_web_middleware = [
    {'after': 'django.middleware.locale.LocaleMiddleware', 'insert': [
        'synnefo.aai.middleware.SynnefoAuthMiddleware',
        'synnefo.api.middleware.ApiAuthMiddleware',
        'synnefo.helpdesk.middleware.HelpdeskMiddleware'
        ]
    }
]

synnefo_static_files = {
    'synnefo.ui': '',
    'synnefo.admin': 'admin',
}
