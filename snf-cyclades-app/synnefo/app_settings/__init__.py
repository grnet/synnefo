synnefo_web_apps = [
    'synnefo.admin',
    'synnefo.api',
    'synnefo.ui',
    'synnefo.db',
    'synnefo.logic',
    'synnefo.plankton',
    'synnefo.vmapi',
    'synnefo.helpdesk',
    'synnefo.nodeapi',
    'synnefo.ui.userdata',
    'synnefo.helpdesk',
]

synnefo_web_middleware = []
synnefo_web_context_processors = ['synnefo.lib.context_processors.cloudbar']

synnefo_static_files = {
    'synnefo.ui': 'ui/static',
    'synnefo.admin': 'admin',
    'synnefo.helpdesk': 'helpdesk',
}
