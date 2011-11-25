# append okeanos_site application to django installed apps
INSTALLED_APPS = list(INSTALLED_APPS) + ['synnefo.okeanos_site']

# for production deployment no DEBUG needed
DEBUG = True

# invitations only, no login page exists
# redirect client to the intro page
LOGIN_URL = "http://host:port/intro"

# redirect to login url (intro) on user logout
LOGOUT_URL = LOGIN_URL

# bypass Shibboleth authentication for /okeanos and /intro pages 
# (they should be available to the public)
AAI_SKIP_AUTH_URLS = list(AAI_SKIP_AUTH_URLS) + ['/about', '/intro', '/okeanos_static']

# change django url configuration
# okeanos_site.urls includes and extends/modifies synnefo.urls
# based on the needs of okeanos aplha release
ROOT_URLCONF = 'synnefo.okeanos_site.urls'

# the url that is linked with okenaos_site.views.index view
OKEANOS_SITE_URL = "/about"

# the url of the synnefo web application (synnefo.ui.views.home)
OKEANOS_APP_URL = "/ui"

# video sources (see okeanos_site/README)
# mp4 should be absolute url for flash player to work (flash video player 
# is the fallback video player for IE)
#
# VIDEOS ARE NOT CONTAINED IN PROJECT FILES
OKEANOS_VIDEO_URL = {
    'mp4': {'src': 'http://okeanos.grnet.gr/intro_video/intro_video.m4v', 'codecs': 'avc1.42E01E, mp4a.40.2'},
    'webm': {'src': 'http://okeanos.grnet.gr/intro_video/intro_video.webm', 'codecs': 'vp8, vorbis'},
    'ogg': {'src': 'http://okeanos.grnet.gr/intro_video/intro_video.ogv', 'codecs': 'theora, vorbis'}
}

# The image placeholder url. Image gets displayed above video position
# as a placeholder when the video is stopped
OKEANOS_VIDEO_POSTER_IMAGE_URL = "/intro_video/intro_video.png"

# flowplayer swf url
# wget http://releases.flowplayer.org/swf/flowplayer-3.2.1.swf
# wget http://releases.flowplayer.org/swf/flowplayer.controls-3.2.0.swf
#
# flowplayer.controls swf should be placed on the same url as flowplayer swf
OKEANOS_VIDEO_FLOWPLAYER_URL = "http://okeanos.grnet.gr/intro_video/flowplayer-3.2.1.swf"
