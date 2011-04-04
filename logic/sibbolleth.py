#
# Business Logic for working with sibbolleth users
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.logic import users

class Tokens:
    SIB_GIVEN_NAME = "givenName"
    SIB_SN = "sn"
    SIB_CN = "cn"
    SIB_DISPLAY_NAME = "displayName"
    SIB_EDU_PERSON_PRINCIPAL_NAME = "eduPersonPrincipalName"
    SIB_EDU_PERSON_AFFILIATION = "eduPersonAffiliation"
    SIB_SCHAC_HOME_ORGANISATION = "schacHomeOrganization"
    SIB_SCHAC_PERSONAL_UNIQUE_CODE = "schacPersonalUniqueCode"
    SIB_GR_EDU_PERSON_UNDERGRADUATE_BRANCH = "grEduPersonUndergraduateBranch"

class NoUniqueToken(object):
    pass


def register_sibbolleth_user(tokens):
    """Registers a sibbolleth user using the input hash as a source for data.
       The token requirements are described in this document
       http://aai.grnet.gr/policy
    """
    
    realname = tokens[Tokens.SIB_GIVEN_NAME] | tokens[Tokens.SIB_GIVEN_NAME]
    is_student = tokens[Tokens.SIB_SCHAC_PERSONAL_UNIQUE_CODE] | \
                 tokens[Tokens.SIB_GR_EDU_PERSON_UNDERGRADUATE_BRANCH]

    unq = tokens[Tokens.SIB_EDU_PERSON_PRINCIPAL_NAME]

    if unq is None:
        raise NoUniqueToken

    if is_student:
        users.register_student(realname, '' ,unq)
    else :
        users.register_professor(realname, '' ,unq)
