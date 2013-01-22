## -*- coding: utf-8 -*-
from django.conf import settings

# Image properties
IMAGE_WIDTH = getattr(settings, 'IMAGE_WIDTH', 210)
WIDTH = getattr(settings, 'WIDTH', 68)
HEIGHT = getattr(settings, 'HEIGHT', 10)

# Path settings
RRD_PREFIX = getattr(settings, 'RRD_PREFIX', "/var/lib/collectd/rrd/")
GRAPH_PREFIX = getattr(settings, 'GRAPH_PREFIX', "/var/cache/snf-stats/")

# Font settings
FONT = getattr(settings, 'FONT', "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSansMono.ttf")
FONT = getattr(settings, 'FONT', "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf")

# Bar settings
BAR_BORDER_COLOR = getattr(settings, 'BAR_BORDER_COLOR', (0x5c, 0xa1, 0xc0))
BAR_BG_COLOR = getattr(settings, 'BAR_BG_COLOR', (0xea, 0xea, 0xea))
