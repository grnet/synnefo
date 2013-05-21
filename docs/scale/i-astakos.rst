.. _i-astakos:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
:ref:`webproject <i-webproject>` ||
astakos ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Astakos Setup
+++++++++++++

The following apply to ``astakos`` node. In the following sections
we will refer to its IP as ``accounts.example.com`` . Make sure
you have db, mq, apache and gunicorn setup already.

IMPORTANT: Currently if astakos coexists with cyclades/pithos roles, your setup is prone to csrf attacks.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First install the corresponding package:

.. code-block:: console

   # apt-get install snf-astakos-app

In `/etc/synnefo/astakos.conf` add:

.. code-block:: console

    CLOUDBAR_LOCATION = 'https://accounts.example.com/static/im/cloudbar/'
    CLOUDBAR_SERVICES_URL = 'https://accounts.example.com/astakos/api/get_services'
    CLOUDBAR_MENU_URL = 'https://accounts.example.com/im/get_menu'

    ASTAKOS_IM_MODULES = ['local']

    ASTAKOS_BASEURL = 'https://accounts.example.com'

    ASTAKOS_SITENAME = '~okeanos @ example.com'
    ASTAKOS_RECAPTCHA_PUBLIC_KEY = '6LeFidMSAAAAAM7Px7a96YQzsBcKYeXCI_sFz0Gk'
    ASTAKOS_RECAPTCHA_PRIVATE_KEY = '6LeFidMSAAAAAFv5U5NSayJJJhr0roludAidPd2M'

    ASTAKOS_RECAPTCHA_USE_SSL = True
    ASTAKOS_RECAPTCHA_ENABLED = True

    ASTAKOS_COOKIE_DOMAIN = 'example.com'

    ASTAKOS_LOGIN_MESSAGES = []
    ASTAKOS_SIGNUP_MESSAGES = []
    ASTAKOS_PROFILE_MESSAGES = []
    ASTAKOS_GLOBAL_MESSAGES = []

    ASTAKOS_PROFILE_EXTRA_LINKS = []
    ASTAKOS_INVITATION_EMAIL_SUBJECT = 'Invitation to %s' % ASTAKOS_SITENAME
    ASTAKOS_GREETING_EMAIL_SUBJECT = 'Welcome to %s' % ASTAKOS_SITENAME
    ASTAKOS_FEEDBACK_EMAIL_SUBJECT = 'Feedback from %s' % ASTAKOS_SITENAME
    ASTAKOS_VERIFICATION_EMAIL_SUBJECT = '%s account activation is needed' % ASTAKOS_SITENAME
    ASTAKOS_ADMIN_NOTIFICATION_EMAIL_SUBJECT = '%s account created (%%(user)s)' % ASTAKOS_SITENAME
    ASTAKOS_HELPDESK_NOTIFICATION_EMAIL_SUBJECT = '%s account activated (%%(user)s)' % ASTAKOS_SITENAME
    ASTAKOS_EMAIL_CHANGE_EMAIL_SUBJECT = 'Email change on %s' % ASTAKOS_SITENAME
    ASTAKOS_PASSWORD_RESET_EMAIL_SUBJECT = 'Password reset on %s' % ASTAKOS_SITENAME

    ASTAKOS_QUOTAHOLDER_TOKEN = '1234'
    ASTAKOS_QUOTAHOLDER_URL = 'https://qh.example.com/quotaholder/v'

    EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
    ASTAKOS_SERVICES = {
        'cyclades': {
            'url': 'https://cyclades.example.com/ui/',
            'resources': [{
                'name':'disk',
                'group':'compute',
                'uplimit':30*1024*1024*1024,
                'unit':'bytes',
                'desc': 'Virtual machine disk size'
                },{
                'name':'cpu',
                'group':'compute',
                'uplimit':6,
                'desc': 'Number of virtual machine processors'
                },{
                'name':'ram',
                'group':'compute',
                'uplimit':6*1024*1024*1024,
                'unit':'bytes',
                'desc': 'Virtual machines'
                },{
                'name':'vm',
                'group':'compute',
                'uplimit':2,
                'desc': 'Number of virtual machines'
                },{
                'name':'network.private',
                'group':'network',
                'uplimit':1,
                'desc': 'Private networks'
                }
            ]
        },
        'pithos+': {
            'url': 'https://pithos.example.com/ui/',
            'resources':[{
                'name':'diskspace',
                'group':'storage',
                'uplimit':5 * 1024 * 1024 * 1024,
                'unit':'bytes',
                'desc': 'Pithos account diskspace'
                }]
        }
    }


If ``astakos`` is on the same node with ``cyclades`` or ``pithos``, add the following
line in `/etc/synnefo/astakos.conf` but please note that your setup will be prone to
csrf attacks:

.. code-block:: console

   MIDDLEWARE_CLASSES.remove('django.middleware.csrf.CsrfViewMiddleware')

Then initialize the Database and register services with:

.. code-block:: console

   # /etc/init.d/gunicorn restart
   # snf-manage syncdb --noinput
   # snf-manage migrate im --delete-ghost-migrations
   # snf-manage loaddata groups
   # snf-manage service-add "home" https://cms.example.com/ home-icon.png
   # snf-manage service-add "cyclades" https://cyclades.example.com/ui/
   # snf-manage service-add "pithos+" https://pithos.example.com/ui/
   # snf-manage astakos-init --load-service-resources
   # snf-manage quota --sync
   # /etc/init.d/gunicorn restart
   # /etc/init.d/apache2 restart

Please note that in case pithos and cyclades nodes are the same node, the pithos url
should be ``https://pithos.example.com/pithos/ui/`` .

Let's create our first user. Go at ``http://accounts.example.com/im/`` and
click the "CREATE ACCOUNT" button and fill all your data at the sign up form.
Then click "SUBMIT". You should now see a green box on the top, which informs
you that you made a successful request and the request has been sent to the
administrators. So far so good, let's assume that you created the user with
username ``user@example.com``.

Now we need to activate that user. Return to a command prompt aand run:

.. code-block:: console

   # snf-manage user-list
   # snf-manage user-modify --set-active 1

where 1 should be the id of the user you previously created.

All this can be done with one command:

.. code-block:: console

   # snf-manage user-add --password=12345 --active user@example.com Name LastName


Test your Setup:
++++++++++++++++

Visit ``http://accounts.example.com/im/`` and login with your credentials.
