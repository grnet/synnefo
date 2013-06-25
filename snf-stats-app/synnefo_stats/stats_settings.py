from django.conf import settings
from synnefo.lib import parse_base_url

BASE_URL = getattr(settings, 'STATS_BASE_URL',
                   'https://stats.example.synnefo.org/stats/')
BASE_HOST, BASE_PATH = parse_base_url(BASE_URL)
