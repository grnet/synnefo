# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
