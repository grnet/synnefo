# Copyright 2011-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.


from contextlib import contextmanager


@contextmanager
def override_settings(settings, **kwargs):
    """
    Helper context manager to override django settings within the provided
    context.

    All keyword arguments provided are set to the django settings object and
    get reverted/removed when the manager exits.

    >>> from synnefo.util.testing import override_settings
    >>> from django.conf import settings
    >>> with override_settings(settings, DEBUG=True):
    >>>     assert settings.DEBUG == True

    The special arguemnt ``prefix`` can be set to prefix all setting keys with
    the provided value.

    >>> from django.conf import settings
    >>> from django.core import mail
    >>> with override_settings(settings, CONTACT_EMAILS=['kpap@grnet.gr'],
    >>>                        prefix='MYAPP_'):
    >>>     from django.core.mail import send_mail
    >>>     send_mail("hello", "I love you kpap", settings.DEFAULT_FROM_EMAIL,
    >>>               settings.MYAPP_CONTACT_EMAILS)
    >>>     assert 'kpap@grnet.gr' in mail.mailbox[0].recipients()

    If you plan to reuse it

    >>> import functools
    >>> from synnefo.util.testing import override_settings
    >>> from django.conf import settings
    >>> myapp_settings = functools.partial(override_settings, prefix='MYAPP_')
    >>> with myapp_settings(CONTACT_EMAILS=['kpap@grnet.gr'])
    >>>     assert settings.MYAPP_CONTACT_EMAILS == ['kpap@grnet.gr']

    """

    _prefix = kwargs.get('prefix', '')
    prefix = lambda key: '%s%s' % (_prefix, key)

    oldkeys = [k for k in dir(settings) if k.upper() == k]
    oldsettings = dict([(k, getattr(settings, k)) for k in oldkeys])

    toremove = []
    for key, value in kwargs.iteritems():
        key = prefix(key)
        if not hasattr(settings, key):
            toremove.append(key)
        setattr(settings, key, value)

    yield

    # Remove keys that didn't exist
    for key in toremove:
        delattr(settings, key)

    # Remove keys that added during the execution of the context
    if kwargs.get('reset_changes', True):
        newkeys = [k for k in dir(settings) if k.upper() == k]
        for key in newkeys:
            if not key in oldkeys:
                delattr(settings, key)

    # Revert old keys
    for key in oldkeys:
        if key == key.upper():
            setattr(settings, key, oldsettings.get(key))


def with_settings(settings, prefix='', **override):
    def wrapper(func):
        def inner(*args, **kwargs):
            with override_settings(settings, prefix=prefix, **override):
                ret = func(*args, **kwargs)
            return ret
        return inner
    return wrapper
