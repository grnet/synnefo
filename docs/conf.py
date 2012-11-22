import sys, os

sys.path.append("../snf-cyclades-app")

project = u'synnefo'
copyright = u'2012, GRNET'
version = '0.12'
release = '0.12'
html_title = 'synnefo ' + version

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'nature'
html_static_path = ['_static']
htmlhelp_basename = 'synnefodoc'

intersphinx_mapping = {
        'pithon': ('http://docs.python.org/', None),
        'django': ('https://docs.djangoproject.com/en/dev/',
                   'https://docs.djangoproject.com/en/dev/_objects/')
}

SYNNEFO_DOCS_BASE_URL = 'http://docs.dev.grnet.gr/'
SYNNEFO_PROJECTS = {
    'synnefo': 'dev',
    'pithos': 'dev',
    'snf-webproject': 'dev',
    'snf-common': 'dev',
    'snf-image': 'dev',
    'snf-cyclades-app': 'dev'
}

for name, ver in SYNNEFO_PROJECTS.iteritems():
    intersphinx_mapping[name.replace("-","")] = (SYNNEFO_DOCS_BASE_URL +
                                                 '%s/%s/' % (name, ver),
                                 None)

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.todo',
              'sphinx.ext.viewcode']
