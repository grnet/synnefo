# Copyright 2011 GRNET S.A. All rights reserved.
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

from util import register_user


class Tokens:
    # these are mapped by the Shibboleth SP software
    SHIB_EPPN = "eppn" # eduPersonPrincipalName
    SHIB_NAME = "Shib-InetOrgPerson-givenName"
    SHIB_SURNAME = "Shib-Person-surname"
    SHIB_CN = "Shib-Person-commonName"
    SHIB_DISPLAYNAME = "Shib-InetOrgPerson-displayName"
    SHIB_EP_AFFILIATION = "Shib-EP-Affiliation"
    SHIB_SESSION_ID = "Shib-Session-ID"


class NoUniqueToken(BaseException):
    def __init__(self, msg):
        self.msg = msg


class NoRealName(BaseException):
    def __init__(self, msg):
        self.msg = msg


def register_shibboleth_user(tokens):
    """Registers a Shibboleth user using the input hash as a source for data."""

    try:
        eppn = tokens[Tokens.SHIB_EPPN]
    except KeyError:
        raise NoUniqueToken("Authentication does not return a unique token")

    if Tokens.SHIB_DISPLAYNAME in tokens:
        realname = tokens[Tokens.SHIB_DISPLAYNAME]
    elif Tokens.SHIB_CN in tokens:
        realname = tokens[Tokens.SHIB_CN]
    elif Tokens.SHIB_NAME in tokens and Tokens.SHIB_SURNAME in tokens:
        realname = tokens[Tokens.SHIB_NAME] + ' ' + tokens[Tokens.SHIB_SURNAME]
    else:
        raise NoRealName("Authentication does not return the user's name")

    affiliation = tokens.get(Tokens.SHIB_EP_AFFILIATION, '')

    register_user(eppn, realname, affiliation)

    return True

