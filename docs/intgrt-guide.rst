.. _intgrt-guide:

Synnefo Integrator's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the complete Synnefo Integrator's Guide

Developer's quick start
=======================

This section describes how to setup quickly a synnefo development environment.
The setup uses ``pip`` and ``virtualenv`` and we assume you do it on a working
debian system. The purpose of this section is to provide the synnefo developer
with a quick installation, so that he can have all the synnefo components
up and running to start developing.

| :ref:`Integrator's quick installation guide <quick-install-intgrt-guide>`
| This guide will walk you through a complete installation using ``pip``.


Synnefo internals
=================

snf-vncauthproxy
----------------

To support OOB console access to the VMs over VNC, the vncauthproxy
daemon must be running on every :ref:`APISERVER <APISERVER_NODE>` node.

.. note:: The Debian package for vncauthproxy undertakes all configuration
   automatically.

Download and install the latest vncauthproxy from its own repository,
at `https://code.grnet.gr/git/vncauthproxy`, or a specific commit:

.. code-block:: console

    $ bin/pip install -e git+https://code.grnet.gr/git/vncauthproxy@INSERT_COMMIT_HERE#egg=vncauthproxy

Create ``/var/log/vncauthproxy`` and set its permissions appropriately.

Alternatively, build and install Debian packages.

.. code-block:: console

    $ git checkout debian
    $ dpkg-buildpackage -b -uc -us
    # dpkg -i ../vncauthproxy_1.0-1_all.deb

.. warning::
    **Failure to build the package on the Mac.**

    ``libevent``, a requirement for gevent which in turn is a requirement for
    vncauthproxy is not included in `MacOSX` by default and installing it with
    MacPorts does not lead to a version that can be found by the gevent
    build process. A quick workaround is to execute the following commands::

        $ cd $SYNNEFO
        $ sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy
        <the above fails>
        $ cd build/gevent
        $ sudo python setup.py -I/opt/local/include -L/opt/local/lib build
        $ cd $SYNNEFO
        $ sudo pip install -e git+https://code.grnet.gr/git/vncauthproxy@5a196d8481e171a#egg=vncauthproxy

.. todo:: Mention vncauthproxy bug, snf-vncauthproxy, inability to install using pip
.. todo:: kpap: fix installation commands


Components
==========

