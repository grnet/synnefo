#
# Business Logic for working with Shibboleth users
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.logic import users


class Tokens:
    SHIB_NAME = "Shib-InetOrgPerson-givenName"
    SHIB_SURNAME = "Shib-Person-surname"
    SHIB_CN = "Shib-Person-commonName"
    SHIB_DISPLAY_NAME = "displayName"
    SHIB_EPPN = "eppn"
    SHIB_EDU_PERSON_AFFILIATION = "shib_ep_primaryaffiliation"
    SHIB_SCHAC_PERSONAL_UNIQUE_CODE = "schacPersonalUniqueCode"
    SHIB_GR_EDU_PERSON_UNDERGRADUATE_BRANCH = "grEduPersonUndergraduateBranch"
    SHIB_SESSION_ID = "Shib-Session-ID"

class NoUniqueToken(BaseException):

    def __init__(self, msg):
        self.msg = msg

class NoRealName(BaseException):

    def __init__(self, msg):
        self.msg = msg

def register_shibboleth_user(tokens):
    """Registers a Shibboleth user using the input hash as a source for data.
       The token requirements are described in:
       http://aai.grnet.gr/policy
    """
    realname = None

    if Tokens.SHIB_SURNAME in tokens:
        realname = tokens[Tokens.SHIB_SURNAME]
    else:
        realname = ''

    if Tokens.SHIB_NAME in tokens:
        realname = tokens[Tokens.SHIB_NAME] + ' ' + realname

    if Tokens.SHIB_CN in tokens:
        realname = tokens[Tokens.SHIB_CN]

    is_student = Tokens.SHIB_SCHAC_PERSONAL_UNIQUE_CODE in tokens or \
                 Tokens.SHIB_GR_EDU_PERSON_UNDERGRADUATE_BRANCH in tokens

    unq = tokens.get(Tokens.SHIB_EPPN)

    if unq is None:
        raise NoUniqueToken("Authentication does not return a unique token")

    if realname is None:
        raise NoRealName("Authentication does not return the user's name")

    if is_student:
        users.register_student(realname, '' , unq)
    else:
        users.register_professor(realname, '' , unq)

    return True
