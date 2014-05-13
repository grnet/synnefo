Upgrade to Synnefo v0.15.1
^^^^^^^^^^^^^^^^^^^^^^^^^^

This release has no notable upgrade steps.

Select Pithos storage backend
=============================

Starting with version 0.15.1, we introduce the ability to select or change the
storage backend for the Pithos Service between NFS and RADOS. In order to use
RADOS, you should first install `snf-image>=0.15` to all Ganeti nodes. For more
information about selecting the Pithos storage backend see
:ref:`select_pithos_storage`.

This is the first version that allows running the whole Synnefo stack over RADOS
only.
