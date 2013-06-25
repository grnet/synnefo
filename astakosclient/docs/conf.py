import sys
import os

sys.path.insert(0, os.path.abspath('..'))
from astakosclient.version import __version__

project = u'nnefo'
copyright = u'2012-2013, GRNET'
version = __version__
release = __version__
html_title = 'synnefo ' + version

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_theme_options = {
    'collapsiblesidebar': 'true',
    'footerbgcolor':    '#55b577',
    'footertextcolor':  '#000000',
    'sidebarbgcolor':   '#ffffff',
    'sidebarbtncolor':  '#f2f2f2',
    'sidebartextcolor': '#000000',
    'sidebarlinkcolor': '#328e4a',
    'relbarbgcolor':    '#55b577',
    'relbartextcolor':  '#ffffff',
    'relbarlinkcolor':  '#ffffff',
    'bgcolor':          '#ffffff',
    'textcolor':        '#000000',
    'headbgcolor':      '#ffffff',
    'headtextcolor':    '#000000',
    'headlinkcolor':    '#c60f0f',
    'linkcolor':        '#328e4a',
    'visitedlinkcolor': '#63409b',
    'codebgcolor':      '#eeffcc',
    'codetextcolor':    '#333333'
}

html_static_path = ['_static']
htmlhelp_basename = 'synnefodoc'

intersphinx_mapping = {
    'pithon': ('http://docs.python.org/', None),
    'django': ('https://docs.djangoproject.com/en/dev/',
               'https://docs.djangoproject.com/en/dev/_objects/')
}

SYNNEFO_DOCS_BASE_URL = 'http://www.synnefo.org/docs'
SYNNEFO_PROJECTS = {
    'synnefo': 'dev',
    'pithos': 'dev',
    'snf-webproject': 'dev',
    'snf-common': 'dev',
    'snf-image': 'dev',
    'snf-cyclades-app': 'dev'
}

for name, ver in SYNNEFO_PROJECTS.iteritems():
    intersphinx_mapping[name.replace("-", "")] = (SYNNEFO_DOCS_BASE_URL +
                                                  '%s/%s/' % (name, ver),
                                                  None)

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.todo',
              'sphinx.ext.viewcode']
