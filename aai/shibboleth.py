# Copyright 2011 GRNET S.A. All rights reserved.
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

# Business Logic for working with sibbolleth users

from synnefo.logic import users


class Tokens:
    SIB_NAME = "Shib-InetOrgPerson-givenName"
    SIB_SURNAME = "Shib-Person-surname"
    SIB_CN = "Shib-Person-commonName"
    SIB_DISPLAY_NAME = "displayName"
    SIB_EPPN = "eppn"
    SIB_EDU_PERSON_AFFILIATION = "shib_ep_primaryaffiliation"
    SIB_SCHAC_PERSONAL_UNIQUE_CODE = "schacPersonalUniqueCode"
    SIB_GR_EDU_PERSON_UNDERGRADUATE_BRANCH = "grEduPersonUndergraduateBranch"
    SIB_SESSION_ID = "Shib-Session-ID"

class NoUniqueToken(BaseException):

    def __init__(self, msg):
        self.msg = msg

class NoRealName(BaseException):

    def __init__(self, msg):
        self.msg = msg

def register_shibboleth_user(tokens):
    """Registers a sibbolleth user using the input hash as a source for data.
       The token requirements are described in:
       http://aai.grnet.gr/policy
    """
    realname = None

    if Tokens.SIB_SURNAME in tokens:
        realname = tokens[Tokens.SIB_SURNAME]
    else:
        realname = ''

    if Tokens.SIB_NAME in tokens:
        realname = tokens[Tokens.SIB_NAME] + ' ' + realname

    if Tokens.SIB_CN in tokens:
        realname = tokens[Tokens.SIB_CN]

    is_student = Tokens.SIB_SCHAC_PERSONAL_UNIQUE_CODE in tokens or \
                 Tokens.SIB_GR_EDU_PERSON_UNDERGRADUATE_BRANCH in tokens

    unq = tokens.get(Tokens.SIB_EPPN)

    if unq is None:
        raise NoUniqueToken("Authentication does not return a unique token")

    if realname is None:
        raise NoRealName("Authentication does not return the user's name")

    if is_student:
        users.register_student(realname, '' , unq)
    else:
        users.register_professor(realname, '' , unq)

    return True
