from django.conf import settings
import datetime

IMAGE_MEDIA_URL = settings.MEDIA_URL+'branding/images/'
COMPANY_NAME = getattr(settings, 'BRANDING_COMPANY_NAME', 'cool company')
COMPANY_NAME_FORMAL = getattr(settings, 'BRANDING_COMPANY_NAME_FORMAL',
	                          'Cool company SARL')
period_default = '2011-%s' % (datetime.datetime.now().year)

# Defaults to 2011-<current_year>
COPYRIGHT_PERIOD = getattr(settings, 'BRANDING_COPYRIGHT_PERIOD', 
						   period_default)

copyright_message = 'Copyright (c) %s %s' % (COPYRIGHT_PERIOD, 
											 COMPANY_NAME_FORMAL)
COPYRIGHT_MESSAGE = getattr(settings, 'BRANDING_COPYRIGHT_MESSAGE', 
						    copyright_message)

COMPANY_URL = getattr(settings, 'BRANDING_COMPANY_URL', 
						    'http://www.coolcompany.com')
SERVICE_NAME = getattr(settings, 'BRANDING_SERVICE_NAME', 'Synnefo')
SERVICE_URL = getattr(settings, 'BRANDING_SERVICE_URL', 'www.Synnefo.org')


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


SERVICE_ABOUT_URL = getattr(settings, 'BRANDING_SERVICE_ABOUT_URL', 
							 'https://okeanos.grnet.gr/about/what/ ')
SERVICE_CONTACT_URL = getattr(settings, 'BRANDING_SERVICE_CONTACT_URL', 
							 'https://accounts.okeanos.grnet.gr/im/feedback ')
SERVICE_SUPPORT_URL = getattr(settings, 'BRANDING_SERVICE_SUPPORT_URL', 
							 'https://okeanos.grnet.gr/support/general/ ')
