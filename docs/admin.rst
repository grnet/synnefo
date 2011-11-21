README.admin - Administration notes

This file contains notes related to administration of a working Synnefo
deployment. This document should be read *after* README.deploy, which contains
step-by-step Synnefo deployment instructions.


Database
========

MySQL: manage.py dbshell seems to ignore the setting of 'init_command'
       in settings.DATABASES


Reconciliation mechanism
========================

On certain occasions, such as a Ganeti or RabbitMQ failure, the VM state in the
system's database may differ from that in the Ganeti installation. The
reconciliation process is designed to bring the system's database in sync with
what Ganeti knows about each VM, and is able to detect the following three
conditions:

 * Stale DB servers without corresponding Ganeti instances
 * Orphan Ganeti instances, without corresponding DB entries
 * Out-of-sync operstate for DB entries wrt to Ganeti instances

The reconciliation mechanism runs as a management command, e.g., as follows:
[PYTHONPATH needs to contain the parent of the synnefo Django project
directory]:

/srv/synnefo$ export PYTHONPATH=/srv:$PYTHONPATH
vkoukis@dev67:~/synnefo [reconc]$ ./manage.py reconcile --detect-all -v 2

Please see ./manage.py reconcile --help for all the details.

The administrator can also trigger reconciliation of operating state manually,
by issuing a Ganeti OP_INSTANCE_QUERY_DATA command on a Synnefo VM, using
gnt-instance info.


Logging
=======

Logging in Synnefo is using Python's logging module. The module is configured
using dictionary configuration, whose format is described here:

http://docs.python.org/release/2.7.1/library/logging.html#logging-config-dictschema

Note that this is a feature of Python 2.7 that we have backported for use in
Python 2.6.

The logging configuration dictionary is defined in settings.d/00-logging.conf
and is broken in 4 separate dictionaries:

  * LOGGING is the logging configuration used by the web app. By default all
    loggers fall back to the main 'synnefo' logger. The subloggers can be
    changed accordingly for finer logging control. e.g. To disable debug
    messages from the API set the level of 'synnefo.api' to 'INFO'.
  
  * DISPATCHER_LOGGING is the logging configuration of the logic/dispatcher.py
    command line tool.
  
  * SNFADMIN_LOGGING is the logging configuration of the snf-admin tool.
    Consider using matching configuration for snf-admin and the synnefo.admin
    logger of the web app.

Please note the following:
  * As of Synnefo v0.7, by default the Django webapp logs to syslog, the
    dispatcher logs to /var/log/synnefo/dispatcher.log and the console,
    snf-admin logs to the console.
  * Different handlers can be set to different logging levels:
    for example, everything may appear to the console, but only INFO and higher
    may actually be stored in a longer-term logfile.


Admin Tools
===========

snf-admin is a tool used to perform various administrative tasks. It needs to
be able to access the django database, so the following should be able to import
the Django settings.

Additionally, administrative tasks can be performed via the admin web interface
located in /admin. Only users of type ADMIN can access the admin pages. To change
the type of a user to ADMIN, snf-admin can be used:

   snf-admin user modify 42 --type ADMIN
