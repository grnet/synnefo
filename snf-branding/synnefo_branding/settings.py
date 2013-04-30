from django.conf import settings
from synnefo.util.version import get_component_version
import datetime


COMPANY_NAME = getattr(settings, 'BRANDING_COMPANY_NAME', 'GRNET')
COMPANY_NAME_FORMAL = getattr(settings, 'BRANDING_COMPANY_NAME_FORMAL',
	                          'GRNET S.A.')
COMPANY_URL = getattr(settings, 'BRANDING_COMPANY_URL', 
					  'https://www.grnet.gr/en/')
SERVICE_NAME = getattr(settings, 'BRANDING_SERVICE_NAME', 'Synnefo')
SERVICE_URL = getattr(settings, 'BRANDING_SERVICE_URL', 
					  'http://www.synnefo.org/')

period_default = '2011-%s' % (datetime.datetime.now().year)

# Defaults to 2011-<current_year>
COPYRIGHT_PERIOD = getattr(settings, 'BRANDING_COPYRIGHT_PERIOD', 
						   period_default)

copyright_message = 'Copyright (c) %s %s' % (COPYRIGHT_PERIOD, 
											 COMPANY_NAME_FORMAL)

# Defaults to Copyright (c) 2011-<current_year>
COPYRIGHT_MESSAGE = getattr(settings, 'BRANDING_COPYRIGHT_MESSAGE', 
						    copyright_message)

# if True, copyright message is visible to footer
SHOW_COPYRIGHT = True


IMAGE_MEDIA_URL = settings.MEDIA_URL+'branding/images/'
FAVICON_URL = getattr(settings, 'BRANDING_FAVICON_URL', 
			settings.MEDIA_URL+'branding/images/favicon.ico')

# Used in Dashboard pages (Astakos)
DASHBOARD_LOGO_URL = getattr(settings, 'BRANDING_DASHBOARD_LOGO_URL', 
					 settings.MEDIA_URL+'branding/images/dashboard_logo.png')
# Used in Compute pages (Cyclades)
COMPUTE_LOGO_URL = getattr(settings, 'BRANDING_COMPUTE_LOGO_URL',
					settings.MEDIA_URL+'branding/images/compute_logo.png')
# Used in Console page for VM (Cyclades)
CONSOLE_LOGO_URL = getattr(settings, 'BRANDING_CONSOLE_LOGO_URL',
					settings.MEDIA_URL+'branding/images/console_logo.png')
# Used in Storage pages (Pithos)
STORAGE_LOGO_URL = getattr(settings, 'BRANDING_STORAGE_LOGO_URL',
					settings.MEDIA_URL+'branding/images/storage_logo.png')
CLOUDBAR_HOME_ICON_URL = getattr(settings, 'CLOUDBAR_HOME_ICON_URL',
					settings.MEDIA_URL+'branding/images/cloudbar_home.png')

# if True, about, support and feeback links are displayed to Compute footer
EXTRA_FOOTER_LINKS = True
SERVICE_ABOUT_URL = getattr(settings, 'BRANDING_SERVICE_ABOUT_URL', 
							 'https://okeanos.grnet.gr/about/what/ ')
SERVICE_CONTACT_URL = getattr(settings, 'BRANDING_SERVICE_CONTACT_URL', 
							 'https://accounts.okeanos.grnet.gr/im/feedback ')
SERVICE_SUPPORT_URL = getattr(settings, 'BRANDING_SERVICE_SUPPORT_URL', 
							 'https://okeanos.grnet.gr/support/general/ ')
 
SYNNEFO_JS_LIB_VERSION = get_component_version('app')
