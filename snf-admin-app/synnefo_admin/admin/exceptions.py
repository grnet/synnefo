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

from django import http
# Add the exceptions that are defined in actions.py in this file too, so that
# all exceptions can exist under the same namespace.
from synnefo_admin.admin.actions import (AdminActionNotPermitted,
                                         AdminActionUnknown,
                                         AdminActionNotImplemented,
                                         AdminActionCannotApply)


class AdminHttp404(http.Http404):

    """404 Exception solely for admin pages."""

    pass


class AdminHttp405(http.Http404):

    """405 Exception solely for admin pages."""

    status = 405
