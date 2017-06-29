import sys, os

sys.path.insert(0, os.path.abspath('../snf-cyclades-app'))
import synnefo
reload(synnefo)
import synnefo.versions
reload(synnefo.versions)
from synnefo.versions.app import __version__

project = u'synnefo'
copyright = u'2010-2017, GRNET S.A.'
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
	'sidebarwidth': '300',
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

htmlhelp_basename = 'synnefodoc'

intersphinx_mapping = {
        'python': ('http://docs.python.org/', None),
        'django': ('https://docs.djangoproject.com/en/dev/',
                   'https://docs.djangoproject.com/en/dev/_objects/')
}

SYNNEFO_PROJECTS = ['synnefo', 'archipelago', 'kamaki', 'snf-image',
                    'snf-image-creator', 'nfdhcpd', 'snf-vncauthproxy',
                    'snf-network']

SYNNEFO_DOCS_BASEURL = 'https://www.synnefo.org/docs/%s/latest/objects.inv'

for project in SYNNEFO_PROJECTS:
    project_url = SYNNEFO_DOCS_BASEURL % project
    intersphinx_mapping[project.replace('-', '')] = (os.path.dirname(project_url), project_url)

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.todo',
              'sphinx.ext.viewcode']
