#
# Business Logic for working with sibbolleth users
#
# Copyright 2010 Greek Research and Technology Network
#

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

class NoUniqueToken(object):

    def __init__(self, msg):
        self.msg = msg
    
    pass

class NoRealName(object):

    def __init__(self, msg):
        self.msg = msg

    pass

def register_shibboleth_user(tokens):
    """Registers a sibbolleth user using the input hash as a source for data.
       The token requirements are described in:
       http://aai.grnet.gr/policy
    """
    realname = None
    print tokens

    if Tokens.SIB_SURNAME in tokens:
        realname = tokens[Tokens.SIB_SURNAME]

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
        users.register_student(realname, '' ,unq)
    else:
        users.register_professor(realname, '' ,unq)

    return True
