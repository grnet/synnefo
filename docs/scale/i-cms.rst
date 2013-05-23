.. _i-cms:

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
:ref:`astakos <i-astakos>` ||
cms ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

CMS Setup
+++++++++

The following apply to ``cms`` node. In the following sections
we will refer to its IP as ``cms.example.com`` . Before install make sure
you have db, apache and gunicorn setup already.

IMPORTANT: Currently cms cannot coexist with astakos, synnefo and pithos roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First install the corresponding package:

.. code-block:: console

   # apt-get install snf-cloudcms


In `/etc/synnefo/cloudcms.conf` add:

.. code-block:: console

    CLOUDBAR_ACTIVE = True
    CLOUDBAR_LOCATION = 'https://accounts.example.com/static/im/cloudbar/'
    CLOUDBAR_SERVICES_URL = 'https://accounts.example.com/im/get_services'
    CLOUDBAR_MENU_URL = 'https://accounts.example.com/im/get_menu'

    WEBPROJECT_SERVE_STATIC = True

Then restart the services and initialize database:

.. code-block:: console

    # /etc/init.d/gunicorn restart
    # /etc/init.d/apache2 restart
    # snf-manage syncdb
    # snf-manage migrate

Here we can load some initial data. Add in `/tmp/sites.json` :

.. code-block:: console

    [
        {
            "pk": 1,
            "model": "sites.site",
            "fields": {
                "domain": "okeanos.grnet.gr",
                "name": "okeanos.grnet.gr"
            }
        }
    ]


and in `/tmp/pages.json`:

.. code-block:: console

    [
        {
            "fields": {
                "_cached_url": "/",
                "_content_title": "",
                "_page_title": "",
                "active": true,
                "creation_date": "2012-11-16 14:52:19",
                "in_navigation": false,
                "language": "en",
                "level": 0,
                "lft": 1,
                "meta_description": "",
                "meta_keywords": "",
                "modification_date": "2012-11-16 14:52:19",
                "navigation_extension": null,
                "override_url": "/",
                "parent": null,
                "publication_date": "2012-11-16 14:50:00",
                "publication_end_date": null,
                "redirect_to": "",
                "rght": 2,
                "site": 1,
                "slug": "okeanos",
                "symlinked_page": null,
                "template_key": "twocolwide",
                "title": "Okeanos",
                "translation_of": null,
                "tree_id": 1
            },
            "model": "page.page",
            "pk": 1
        },
        {
            "fields": {
                "ordering": 0,
                "parent": 1,
                "region": "main",
                "text": "Welcome to Okeanos!!\r\n\r\n"
            },
            "model": "page.rawcontent",
            "pk": 1
        }
    ]



and finally run:

.. code-block:: console

    # snf-manage loaddata /tmp/sites.json
    # snf-manage loaddata /tmp/page.json
    # snf-manage createsuperuser --username=admin --email=admin@example --noinput


Test your Setup:
++++++++++++++++

Visit https://cms.example.com/
