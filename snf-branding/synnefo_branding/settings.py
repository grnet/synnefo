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

## Copyright and footer options
######################

# If True, Copyright message will appear at the footer of the Compute and
# Dashboard UI
SHOW_COPYRIGHT = getattr(settings, 'BRANDING_SHOW_COPYRIGHT', True)
copyright_period_default = '2011-%s' % (datetime.datetime.now().year)
copyright_message_default = 'Copyright (c) %s %s' % (copyright_period_default,
                                                     COMPANY_NAME)
# Defaults to Copyright (c) 2011-<current_year> GRNET.
COPYRIGHT_MESSAGE = getattr(settings, 'BRANDING_COPYRIGHT_MESSAGE',
                            copyright_message_default)
SYNNEFO_VERSION = get_component_version('common')

# Footer message appears above Copyright message at the Compute templates
# and the Dashboard UI. Accepts html tags
FOOTER_EXTRA_MESSAGE = getattr(settings, 'BRANDING_FOOTER_EXTRA_MESSAGE', '')
