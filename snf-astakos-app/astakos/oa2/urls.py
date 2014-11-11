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

from astakos.oa2.backends import DjangoBackend

from astakos.oa2 import settings

oa2_backend = DjangoBackend(endpoints_prefix=settings.ENDPOINT_PREFIX,
                            token_endpoint=settings.TOKEN_ENDPOINT,
                            token_length=settings.TOKEN_LENGTH,
                            token_expires=settings.TOKEN_EXPIRES,
                            authorization_endpoint=
                            settings.AUTHORIZATION_ENDPOINT,
                            authorization_code_length=
                            settings.AUTHORIZATION_CODE_LENGTH,
                            redirect_uri_limit=
                            settings.MAXIMUM_ALLOWED_REDIRECT_URI_LENGTH)
urlpatterns = oa2_backend.get_url_patterns()
