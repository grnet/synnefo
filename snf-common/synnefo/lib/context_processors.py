from django.utils.safestring import mark_safe
from django.conf import settings

def cloudbar(request):
    """
    Django context processor that applies all cloudbar settings in response
    context plus a ready to use pre rendered script html tag containing valid
    javascript code for cloudbar to display.

    To use it add ``synnefo.lib.context_processors.cloudbar`` in your project's
    ``TEMPLATE_CONTEXT_PROCESSORS setting`` (snf-webproject already does).

    Then in your base html template::

        <html>
        ....
        <head>
        ...
        {% if CLOUDBAR_ACTIVE %}
            {{ CLOUDBAR_CODE }}
        {% endif %}
        </head>
        <body>
        ....
        </body>
        </html>


    """

    CB_ACTIVE = getattr(settings, 'CLOUDBAR_ACTIVE', True)
    CB_LOCATION = getattr(settings, 'CLOUDBAR_LOCATION',
            'https://accounts.okeanos.grnet.gr/static/im/cloudbar/')
    CB_COOKIE_NAME = getattr(settings, 'CLOUDBAR_COOKIE_NAME',
            'okeanos_account')
    CB_ACTIVE_SERVICE = getattr(settings, 'CLOUDBAR_ACTIVE_SERVICE',
            'cloud')
    CB_SERVICES_URL = getattr(settings, 'CLOUDBAR_SERVICES_URL',
            'https://accounts.okeanos.grnet.gr/im/get_services')
    CB_MENU_URL = getattr(settings, 'CLOUDBAR_MENU_URL',
            'https://accounts.okeanos.grnet.gr/im/get_menu')
    CB_HEIGHT = getattr(settings, 'CLOUDBAR_HEIGHT',
            '35')
    CB_BGCOLOR = getattr(settings, 'CLOUDBAR_BACKGROUND_COLOR',
            '#000000')

    CB_CODE = """
    <script type="text/javascript">
        var CLOUDBAR_LOCATION = "%(location)s";
        var CLOUDBAR_COOKIE_NAME = "%(cookie_name)s";
        var CLOUDBAR_ACTIVE_SERVICE = "%(active_service)s";
        var GET_SERVICES_URL = "%(services_url)s";
        var GET_MENU_URL = "%(menu_url)s";
        var CLOUDBAR_HEIGHT = '%(height)s';

        $(document).ready(function(){
            $.getScript(CLOUDBAR_LOCATION + 'cloudbar.js');
        });

    </script>
    <style>
        body {
            border-top: %(height)spx solid %(bg_color)s;
        }
        body .cloudbar {
            height: %(height)spx;
        }
    </style>
""" % {'location': CB_LOCATION,
       'active_service': CB_ACTIVE_SERVICE,
       'cookie_name': CB_COOKIE_NAME,
       'services_url': CB_SERVICES_URL,
       'menu_url': CB_MENU_URL,
       'height': str(CB_HEIGHT),
       'bg_color': CB_BGCOLOR}

    CB_CODE = mark_safe(CB_CODE)

    return {
        'CLOUDBAR_ACTIVE': CB_ACTIVE,
        'CLOUDBAR_LOCATION': CB_LOCATION,
        'CLOUDBAR_COOKIE_NAME': CB_COOKIE_NAME,
        'CLOUDBAR_ACTIVE_SERVICE': CB_ACTIVE_SERVICE,
        'CLOUDBAR_SERVICES_URL': CB_SERVICES_URL,
        'CLOUDBAR_MENU_URL': CB_MENU_URL,
        'CLOUDBAR_CODE': CB_CODE
    }

