from django.conf import settings
from synnefo.util.version import get_component_version
import datetime

## Service and company names/urls
######################

SERVICE_NAME = getattr(settings, 'BRANDING_SERVICE_NAME', 'Synnefo')
SERVICE_URL = getattr(settings, 'BRANDING_SERVICE_URL', 
					  'http://www.synnefo.org/')
COMPANY_NAME = getattr(settings, 'BRANDING_COMPANY_NAME', 'GRNET')
COMPANY_URL = getattr(settings, 'BRANDING_COMPANY_URL', 
					  'https://www.grnet.gr/en/')


## Images
######################

# The default path to the folder that contains all branding images
IMAGE_MEDIA_URL = getattr(settings, 'BRANDING_IMAGE_MEDIA_URL', 
						  settings.MEDIA_URL+'branding/images/')
 
# You can replace any image by providing its absolute path
# example: 'https://synnefo.org/uploads/images/my_image.png'
# The service favicon 
FAVICON_URL = getattr(settings, 'BRANDING_FAVICON_URL',
        	   		  IMAGE_MEDIA_URL+'favicon.ico')
# Logo used in Dashboard pages (Astakos)
DASHBOARD_LOGO_URL = getattr(settings, 'BRANDING_DASHBOARD_LOGO_URL', 
					 		 IMAGE_MEDIA_URL+'dashboard_logo.png')
# Logo used in Compute pages (Cyclades)
COMPUTE_LOGO_URL = getattr(settings, 'BRANDING_COMPUTE_LOGO_URL',
						   IMAGE_MEDIA_URL+'compute_logo.png')
# Logo used in Console page for VM (Cyclades)
CONSOLE_LOGO_URL = getattr(settings, 'BRANDING_CONSOLE_LOGO_URL',
						   IMAGE_MEDIA_URL+'console_logo.png')
# Logo used in Storage pages (Pithos)
STORAGE_LOGO_URL = getattr(settings, 'BRANDING_STORAGE_LOGO_URL',
						   IMAGE_MEDIA_URL+'storage_logo.png') 

## Copyright options
######################

# If True, Copyright message will appear at the footer of the Compute and 
# Dashboard UI 
SHOW_COPYRIGHT = getattr(settings, 'BRANDING_SHOW_COPYRIGHT', False)
copyright_period_default = '2011-%s' % (datetime.datetime.now().year)
# Defaults to 2011-<current_year>
COPYRIGHT_PERIOD = getattr(settings, 'BRANDING_COPYRIGHT_PERIOD', 
						   copyright_period_default)
# Formal company name appears in copyright message
COMPANY_NAME_FORMAL = getattr(settings, 'BRANDING_COMPANY_NAME_FORMAL',
	                          'GRNET S.A.')
copyright_message_default = 'Copyright (c) %s %s' % (COPYRIGHT_PERIOD, 
											 COMPANY_NAME_FORMAL)
# Defaults to Copyright (c) 2011-<current_year> GRNET S.A.
COPYRIGHT_MESSAGE = getattr(settings, 'BRANDING_COPYRIGHT_MESSAGE', 
						    copyright_message_default)


## Footer links
######################

# If True, "about", "contact" and "support" links are displayed at the footer 
# of the Compute UI 
SHOW_FOOTER_LINKS = getattr(settings, 'BRANDING_SHOW_FOOTER_LINKS', True)
SERVICE_ABOUT_URL = getattr(settings, 'BRANDING_SERVICE_ABOUT_URL', 
							'https://synnefo.org/about')
SERVICE_CONTACT_URL = getattr(settings, 'BRANDING_SERVICE_CONTACT_URL', 
							 'https://synnefo.org/contact')
SERVICE_SUPPORT_URL = getattr(settings, 'BRANDING_SERVICE_SUPPORT_URL', 
							 'https://synnefo.org/support')
 
SYNNEFO_JS_LIB_VERSION = get_component_version('app')
