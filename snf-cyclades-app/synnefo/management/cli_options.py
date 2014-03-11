# Copyright 2014 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#

import astakosclient
from django.conf import settings
from optparse import make_option, OptionValueError
from snf_django.management.utils import parse_bool


class WrappedOptions(object):
    """Wrapper class to provide access to options as object attributes"""
    def __init__(self, options_dict):
        self.__dict__.update(options_dict)


def make_boolean_option(*args, **kwargs):
    """Helper function to create a boolean option."""
    def parse_boolean_option(option, option_str, value, parser):
        if value is not None:
            try:
                value = parse_bool(value)
            except ValueError:
                choices = "True, False"
                raise OptionValueError(
                    "option %s: invalid choice: %r (choose from %s)"
                    % (option, value, choices))
        setattr(parser.values, option.dest, value)

    return make_option(*args,
                       metavar="True|False",
                       type=str,
                       action="callback",
                       callback=parse_boolean_option,
                       **kwargs)


def parse_user_option(option, option_str, value, parser):
    """Callback to parser -u/--user option

    Translate uuid <-> email and add 'user_id' and 'user_email' to command
    options.

    """
    astakos = astakosclient.AstakosClient(settings.CYCLADES_SERVICE_TOKEN,
                                          settings.ASTAKOS_AUTH_URL,
                                          retry=2)
    try:
        if "@" in value:
            email = value
            uuid = astakos.service_get_uuid(email)
        else:
            uuid = value
            email = astakos.service_get_username(uuid)
    except astakosclient.errors.NoUUID:
        raise OptionValueError("User with email %r does not exist" % email)
    except astakosclient.errors.NoUserName:
        raise OptionValueError("User with uuid %r does not exist" % uuid)
    except astakosclient.errors.AstakosClientException as e:
        raise OptionValueError("Failed to get user info:\n%r" % e)

    setattr(parser.values, 'user_id', uuid)
    setattr(parser.values, 'user_email', email)


USER_OPT = make_option("-u", "--user",
                       default=None, type=str,
                       action="callback", callback=parse_user_option,
                       help="Specify the UUID or email of the user")
