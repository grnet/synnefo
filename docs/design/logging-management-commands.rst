===================================================
Logging mechanism for Synnefo's management commands
===================================================


Abstract
========

Log all stdout and stderr output of every invocation of snf-manage, on unique
filenames under a given directory.


Current state and shortcomings
==============================

All Synnefo's management commands are written as custom django-admin commands.
This means that every management command is in fact a class that extends
Django's BaseCommand class.

Django's *BaseCommand* provides the attributes ``self.stdout`` and
``self.stderr`` and Django's documentation encourages the users to use these
attributes if they wish to write to the console. Django doesn't provide an
option to write the output to files and the user has to implement this
explicitly when implementing the ``handle`` method.

We would like to extend the above mechanism to allow every ``snf-manage``
command to log all stdout and stderr output on a unique filename under a given
directory. The implementation should change nothing in the way that users write
management commands (only acceptable change is that the new commands may have
to inherit a new class and not the *BaseCommand* one). This means that
existing management commands should play out of the box and also that the
logging mechanism will globally apply to all of them.

A new Synnefo setting named **LOGGER_EXCLUDE_COMMANDS** has been added that
specifies which commands will not be logged. By default, commands that do not
alter the state of the server (i.e. \*-list and \*-show commands) will be
excluded from the logging mechanism. One can disable this logging mechanism all
together by setting the above variable to ".\*".


Proposed changes
================

In this section we will try to explain the way that the new logging mechanism
will be implemented as well as the reasons behind these decisions.

As we previously saw, we want the logging mechanism to be global and to work
for all the ``snf-manage`` commands without extra effort. This means that the
management commands will continue to use the ``self.stdout`` and
``self.stderr`` attributes from *BaseCommand* class to provide console
output. Therefor we have to provide our own ``self.stdout`` and ``self.stderr``
objects that will preserve the previous functionality and log to files at the
same time. There are two ways to achieve that:

Patch the Django's *BaseCommand* class and replace ``self.stdout`` and
``self.stderr`` attributes.

    This solution requires the minimum amount of changes to the management
    commands' code as they will use our patched version of *BaseCommand*.
    The downside is that we have to patch a library provided class. We are not
    encouraging these type of patches because it obfuscates the code (the
    programmer is expecting to use Django's *BaseCommand* class, not ours)
    and does not preserve compatibility with other Django versions (if the
    implementation of Django's *BaseCommand* changes our patch will not
    work).

Create a new class that extends Django's *BaseCommand*.

    The downside of this solution is that we have to change the existing code
    so all management commands will inherit our new class and not Django's
    *BaseCommand*. But we find this solution to be cleaner.

For the above reasons we decided to go with the second option.

Django's ``self.stdout`` and ``self.stderr`` are implemented as *OutputWrapper*
objects. We will create our own class (**SynnefoOutputWrapper**) which will use
python's logging library to handle the file part of the logging and the
original *OutputWrapper* object to handle the console part (since we want to
preserve the functionality of Django's *OutputWrapper* and the style functions
it uses to pretty print the messages).

Our new class has to be a **descriptor**. This is because *BaseCommand* doesn't
initialize the ``stdout`` and ``stderr`` attributes at ``__init__`` but sets
them only when it needs to (meaning inside the *execute* method).

The above classes will be written in snf-django-lib package meaning that all
the other packages will have a dependency in snf-django-lib.

We will combine timestamp, command name and PID to form unique names, e.g.:
20140120113432-server-modify-4564, where "4564" was the PID. The timestamp will
be first so that files will be chronologically sorted.


Implementation details
======================

The implementation will follow the following steps:

- Change current management commands to use ``self.stdout`` and ``self.stderr``
  to provide console output instead of ``sys.stdout``, ``print`` or anything
  else. This change complies with Django's documentation.

- Write a new class that will replace Django's *OutputWrapper*.

- Change the **SynnefoCommand** class so that it will extend Django's
  *BaseCommand* and will replace ``stdout`` and ``stderr`` attributes.

- Change all management commands to inherit the **SynnefoBaseCommand** class.

- Update package dependencies.

- Add a new Synnefo setting to allow the user to change the directory where
  the output will be saved.
