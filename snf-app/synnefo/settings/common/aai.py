# -*- coding: utf-8 -*-
#
# AAI configuration
#####################

# Shibboleth-enabled path under the APP_INSTALL_URL.
LOGIN_URL = "https://login.okeanos.grnet.gr"

# Set the expiration time of newly created auth tokens
# to be this many hours after their creation time.
AUTH_TOKEN_DURATION = 30 * 24

# Enable receiving a temporary auth token (using the ?test URL parameter) that
# bypasses the authentication mechanism.
#
# WARNING, ACHTUNG, README, etc: DO NOT ENABLE THIS ON DEPLOYED VERSIONS!
#
BYPASS_AUTHENTICATION = False
BYPASS_AUTHENTICATION_TOKEN = '5e41595e9e884543fa048e07c1094d74'

# Urls that bypass Shibboleth authentication
AAI_SKIP_AUTH_URLS = ['/api', '/plankton', '/invitations/login']

