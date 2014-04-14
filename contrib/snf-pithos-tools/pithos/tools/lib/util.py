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

import os

DEFAULT_URL = 'https://pithos.example.synnefo.org/v1'
DEFAULT_USER = 'test'
DEFAULT_TOKEN = '0000'


def get_user():
    try:
        return os.environ['PITHOS_USER']
    except KeyError:
        return DEFAULT_USER


def get_auth():
    try:
        return os.environ['PITHOS_TOKEN']
    except KeyError:
        return DEFAULT_TOKEN


def get_url():
    try:
        return os.environ['PITHOS_URL'].rstrip('/')
    except KeyError:
        return DEFAULT_URL
