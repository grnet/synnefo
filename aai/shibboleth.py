#
# Business Logic for working with Shibboleth users
#
# Copyright 2010-2011 Greek Research and Technology Network
#

from synnefo.logic import users

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

    if Tokens.SHIB_DISPLAYNAME in tokens:
        realname = tokens[Tokens.SHIB_DISPLAYNAME]
    elif Tokens.SHIB_CN in tokens:
        realname = tokens[Tokens.SHIB_CN]
    elif Tokens.SHIB_NAME in tokens and Tokens.SHIB_SURNAME in tokens:
        realname = tokens[Tokens.SHIB_NAME] + ' ' + tokens[Tokens.SHIB_SURNAME]
    else:
        raise NoRealName("Authentication does not return the user's name")

    try:
        affiliation = tokens[Tokens.SHIB_EP_AFFILIATION]
    except KeyError:
        affiliation = 'member'

    try:
        eppn = tokens[Tokens.SHIB_EPPN]
    except KeyError:
        raise NoUniqueToken("Authentication does not return a unique token")

    if affiliation == 'student':
        users.register_student(realname, '' , eppn)
    else:
        # this includes faculty but also staff, alumni, member, other, ...
        users.register_professor(realname, '' , eppn)

    return True
