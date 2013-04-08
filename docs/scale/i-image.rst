.. _i-image:

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
:ref:`qh <i-qh>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Backends
++++++++

:ref:`ganeti <i-ganeti>` ||
image ||
:ref:`gtools <i-gtools>` ||
:ref:`network <i-network>`

snf-image Setup
~~~~~~~~~~~~~~~

The following apply to ``ganeti`` nodes.

Firstly mount the ``pithos`` nfs mount point. Assuming that ``pithos`` node
(the one who does the NFS export) is node1.example.com, append the following
line in `/etc/fstab`:

.. code-block:: console

   node1:/pithos /srv/pithos nfs4 defaults,rw,noatime,nodiratime,intr,rsize=1048576,wsize=1048576,noacl

and then:

.. code-block:: console

   apt-get install -t squeeze-backports nfs-common
   mkdir /srv/pithos
   mount /srv/pithos

.. code-block:: console

   # apt-get install snf-image-host

Append this lines in `/etc/snf-image/default`

.. code-block:: console

    PITHOS_DB="postgresql://synnefo:example_passw0rd@db.example.com:5432/snf_pithos"
    PITHOS_DATA="/srv/pithos/data"
    PROGRESS_MONITOR='snf-progress-monitor'


and create snf-image-helper with:

.. code-block:: console

   # snf-image-update-helper -y


Test your Setup:
++++++++++++++++
