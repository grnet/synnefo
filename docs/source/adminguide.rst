Administrator Guide
===================

Simple Setup
------------

Assuming a clean debian squeeze (stable) installation, use the following steps to run the software.

Install packages::

  apt-get install git python-django python-django-south python-setuptools python-sphinx python-httplib2
  apt-get install apache2 libapache2-mod-wsgi

Get the source::

  cd /
  git clone https://code.grnet.gr/git/astakos

Setup the files::

  cd /astakos/astakos
  python manage.py syncdb (At this point you will prompt to create a superuser)
  python manage.py migrate im 0001 --fake
  python manage.py migrate im
  python loaddata im/fixtures/admin_user.json (Load additional information for the newly created superuser)
  cd /astakos
  python setup.py build_sphinx
  python manage runserver

It is advised that you create a ``settings.local`` file to place any configuration overrides (at least change ``SECRET_KEY``).

Twitter Setup
-------------
