from django.views.generic.simple import direct_to_template
from django.conf import settings

OKEANOS_STATIC = getattr(settings, 'OKEANOS_STATIC_URL', '/okeanos_static/')
OKEANOS_SITE_URL = getattr(settings, 'OKEANOS_SITE_URL', '/okeanos')
OKEANOS_VIDEO_URL = getattr(settings, 'OKEANOS_VIDEO_URL', '')
OKEANOS_APP_URL = getattr(settings, 'OKEANOS_APP_URL', '/')

# needed for flash fallback video
OKEANOS_MP4_VIDEO_URL = OKEANOS_VIDEO_URL.get('mp4', {}).get('src', False)

context = {
    'OKEANOS_STATIC_URL': OKEANOS_STATIC,
    'OKEANOS_SITE_URL': OKEANOS_SITE_URL,
    'OKEANOS_VIDEO_URL': OKEANOS_VIDEO_URL,
    'OKEANOS_APP_URL': OKEANOS_APP_URL,
    'OKEANOS_MP4_VIDEO_URL': OKEANOS_MP4_VIDEO_URL,
    'OKEANOS_VIDEO_POSTER_IMAGE_URL': settings.OKEANOS_VIDEO_POSTER_IMAGE_URL,
    'OKEANOS_VIDEO_FLOWPLAYER_URL': settings.OKEANOS_VIDEO_FLOWPLAYER_URL,
    'VIDEO_WIDTH': 640,
    'VIDEO_HEIGHT': 360
}

def intro(request):
    return direct_to_template(request, "okeanos/intro.html", context)

def index(request):
    return direct_to_template(request, "okeanos/index.html", context)

