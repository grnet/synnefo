# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from django.conf import settings

ACCOUNT_AUTHENTICATION_FAILED           =   'Cannot authenticate account.'
ACCOUNT_ALREADY_ACTIVE                  =   'Account is already active.'
ACCOUNT_PENDING_ACTIVATION              =   'Your request is pending activation.'
ACCOUNT_PENDING_MODERATION              =   'Your request is pending moderation.'
ACCOUNT_INACTIVE                        =   'Your account is disabled.'
ACCOUNT_RESEND_ACTIVATION               =   'You have not followed the activation link. <a href="%(send_activation_url)s">Resend activation email?</a>'
INACTIVE_ACCOUNT_CHANGE_EMAIL           =   ''.join([ACCOUNT_RESEND_ACTIVATION, ' or <a href="%(signup_url)s">Provide new email?</a>'])

ACCOUNT_PENDING_ACTIVATION_HELP         =   'If you haven\'t received activation email, be sure to check your spam folder.'

ACCOUNT_ACTIVATED                       =   'Congratulations. Your account has' + \
                                            ' been activated and you have been' + \
                                            ' automatically signed in to your account.'
PASSWORD_RESET_DONE                     =   'A mail with details on how to change your password was sent.'
PASSWORD_RESET_CONFIRM_DONE             =   'Password changed. You can now login using your new password.'

ACCOUNT_RESEND_ACTIVATION_PROMPT        =   'Resend activation mail'
ACCOUNT_USER_ACTIVATION_PENDING         =   'You have not followed the activation link'

ACCOUNT_UNKNOWN                         =   'There is no such account.'
TOKEN_UNKNOWN                           =   'There is no user matching this token.'

PROFILE_UPDATED                         =   'Profile has been updated successfully.'
FEEDBACK_SENT                           =   'Feedback successfully sent.'
EMAIL_CHANGED                           =   'Account email has been changed successfully.'
EMAIL_CHANGE_REGISTERED                 =   'Change email request has been registered succefully. \
                                               You are going to receive a verification email in the new address.'

OBJECT_CREATED                          =   'The %(verbose_name)s was created successfully.'
USER_JOINED_GROUP                       =   '%(realname)s has been successfully joined the group.'
USER_LEFT_GROUP                         =   '%(realname)s has been successfully left the group.'
USER_MEMBERSHIP_REJECTED                =   '%(realname)s\'s request to join the group has been rejected.'
MEMBER_REMOVED                          =   '%(realname)s has been successfully removed from the group.'
BILLING_ERROR                           =   'Service response status: %(status)d'
LOGOUT_SUCCESS                          =   'You have successfully logged out.'
LOGIN_SUCCESS                           =   'You have successfully logged in.'

GENERIC_ERROR                           =   'Something wrong has happened. \
                                               Please contact the administrators for more details.'

MAX_INVITATION_NUMBER_REACHED   =           'There are no invitations left.'
GROUP_MAX_PARTICIPANT_NUMBER_REACHED    =   'Group maximum participant number has been reached.'
PROJECT_MAX_PARTICIPANT_NUMBER_REACHED  =   'Project maximum participant number has been reached.'
NO_APPROVAL_TERMS                       =   'There are no approval terms.'
PENDING_EMAIL_CHANGE_REQUEST            =   'There is already a pending change email request. ' + \
                                            'Submiting a new email will cancel any previous requests.'
OBJECT_CREATED_FAILED                   =   'The %(verbose_name)s creation failed: %(reason)s.'
GROUP_JOIN_FAILURE                      =   'Failed to join group.'
PROJECT_JOIN_FAILURE                    =   'Failed to join project.'
GROUPKIND_UNKNOWN                       =   'There is no such a group kind'
NOT_MEMBER                              =   'User is not member of the group.'
NOT_OWNER                               =   'User is not a group owner.'
OWNER_CANNOT_LEAVE_GROUP                =   'Owner cannot leave the group.'

# Field validation fields
REQUIRED_FIELD                          =   'This field is required.'
EMAIL_USED                              =   'This email address is already in use. Please supply a different email address.'
SHIBBOLETH_EMAIL_USED                   =   'This email is already associated with another shibboleth account.'
SHIBBOLETH_INACTIVE_ACC                 =   'This email is already associated with an inactive account. \
                                               You need to wait to be activated before being able to switch to a shibboleth account.'
SHIBBOLETH_MISSING_EPPN                 =   'Missing unique token in request.'
SHIBBOLETH_MISSING_NAME                 =   'Missing user name in request.'

SIGN_TERMS                              =   'You have to agree with the terms.'
CAPTCHA_VALIDATION_ERR                  =   'You have not entered the correct words.'
SUSPENDED_LOCAL_ACC                     =   'Local login is not the current authentication method for this account.'
UNUSABLE_PASSWORD                       =   'This account has not a usable password.'
EMAIL_UNKNOWN                           =   'That e-mail address doesn\'t have an associated user account. \
                                               Are you sure you\'ve registered?'
INVITATION_EMAIL_EXISTS                 =   'There is already invitation for this email.'
INVITATION_CONSUMED_ERR                 =   'Invitation is used.'
UNKNOWN_USERS                           =   'Unknown users: %s'
UNIQUE_EMAIL_IS_ACTIVE_CONSTRAIN_ERR    =   'Another account with the same email & is_active combination found.'
INVALID_ACTIVATION_KEY                  =   'Invalid activation key.'
NEW_EMAIL_ADDR_RESERVED                 =   'The new email address is reserved.'
EMAIL_RESERVED                          =   'Email: %(email)s is reserved'
NO_LOCAL_AUTH                           =   'Local login is not the current authentication method for this account.'
SWITCH_ACCOUNT_FAILURE                  =   'Account failed to switch. Invalid parameters.'
SWITCH_ACCOUNT_SUCCESS_WITH_PROVIDER    =   'Account failed to switch to %(provider)s.'
SWITCH_ACCOUNT_SUCCESS                  =   'Account successfully switched to %(provider)s.'

# Field help text
ADD_GROUP_MEMBERS_Q_HELP                =   'Add comma separated user emails, eg. user1@user.com, user2@user.com'
ASTAKOSUSER_GROUPS_HELP                 =   'In addition to the permissions manually assigned, \
                                               this user will also get all permissions granted to each group he/she is in.'
EMAIL_CHANGE_NEW_ADDR_HELP              =   'Your old email address will be used until you verify your new one.'

EMAIL_SEND_ERR                          =   'Failed to send %s.'
ADMIN_NOTIFICATION_SEND_ERR             =   EMAIL_SEND_ERR % 'admin notification'
VERIFICATION_SEND_ERR                   =   EMAIL_SEND_ERR % 'verification'
INVITATION_SEND_ERR                     =   EMAIL_SEND_ERR % 'invitation'
GREETING_SEND_ERR                       =   EMAIL_SEND_ERR % 'greeting'
FEEDBACK_SEND_ERR                       =   EMAIL_SEND_ERR % 'feedback'
CHANGE_EMAIL_SEND_ERR                   =   EMAIL_SEND_ERR % 'feedback'
NOTIFICATION_SEND_ERR                   =   EMAIL_SEND_ERR % 'notification'
DETAILED_NOTIFICATION_SEND_ERR          =   'Failed to send %(subject)s notification to %(recipients)s.'

MISSING_NEXT_PARAMETER                  =   'No next parameter'

INVITATION_SENT                         =   'Invitation sent to %(email)s.'
VERIFICATION_SENT                       =   'Registration completed but account is not active yet. Account activation link was sent to your email address.'
SWITCH_ACCOUNT_LINK_SENT                =   'This email is already associated with another local account. \
                                             To change this account to a shibboleth one follow the link in the verification email sent to %(email)s. \
                                             Otherwise just ignore it.'
NOTIFICATION_SENT                       =   'Your request for an account was successfully received and is now pending approval. \
                                               You will be notified by email in the next few days. \
                                               Thanks for your interest in ~okeanos! The GRNET team.'
ACTIVATION_SENT                         =   'An email containing your activation link was sent to your email address.'

REGISTRATION_COMPLETED                  =   'Registration completed you can now login to your account.'

NO_RESPONSE                             =   'There is no response.'
NOT_ALLOWED_NEXT_PARAM                  =   'Not allowed next parameter.'
MISSING_KEY_PARAMETER                   =   'Missing key parameter.'
INVALID_KEY_PARAMETER                   =   'Invalid key.'
DOMAIN_VALUE_ERR                        =   'Enter a valid domain.'
QH_SYNC_ERROR                           =   'Failed to get synchronized with quotaholder.'
UNIQUE_PROJECT_NAME_CONSTRAIN_ERR       =   'The project name (as specified in its application\'s definition) must be unique among all active projects.'
INVALID_PROJECT                         =   'Project %(id)s is invalid.'
NOT_ALIVE_PROJECT                       =   'Project %(id)s is not alive.'
NOT_ALLOWED                             =   'You do not have the permissions to perform this action.'
MEMBER_NUMBER_LIMIT_REACHED             =   'Maximum participant number has been reached.'
MEMBER_JOIN_POLICY_CLOSED               =   'The project member join policy is closed.'
MEMBER_LEAVE_POLICY_CLOSED              =   'The project member leave policy is closed.'
NOT_MEMBERSHIP_REQUEST                  =   'There is no such a membership request.'
MEMBERSHIP_REQUEST_EXISTS               =   'There is alreary such a membership request.'
NO_APPLICANT                            =   'Project application requires an applicant. None found.'
ADD_PROJECT_MEMBERS_Q_HELP              =   'Add comma separated user emails, eg. user1@user.com, user2@user.com'
MISSING_IDENTIFIER                      =   'Missing identifier.'
UNKNOWN_USER_ID                         =   'There is no user identified by %s.'
UNKNOWN_PROJECT_APPLICATION_ID          =   'There is no project application identified by %s.'
UNKNOWN_IDENTIFIER                      =   'Unknown identidier.'
PENDING_MEMBERSHIP_LEAVE                =   'Your request is pending acception.'
USER_JOINED_PROJECT                     =   '%(realname)s has been successfully joined the project.'
USER_LEFT_PROJECT                       =   '%(realname)s has been successfully left the project.'

# Auth providers messages
AUTH_PROVIDER_NOT_ACTIVE                     =   "'%(provider)s' is disabled"
AUTH_PROVIDER_NOT_ACTIVE_FOR_LOGIN           =   "Login using '%(provider)s' is disabled"
AUTH_PROVIDER_NOT_ACTIVE_FOR_USER            =   "You cannot login using '%(provider)s'"
AUTH_PROVIDER_NOT_ACTIVE_FOR_CREATE          =   "Signup using '%(provider)s' is disabled."
AUTH_PROVIDER_NOT_ACTIVE_FOR_ADD             =   "You cannot add %(provider)s login method."
AUTH_PROVIDER_ADDED                          =   "New login method added."
AUTH_PROVIDER_ADD_FAILED                     =   "Failed to add new login method."
AUTH_PROVIDER_ADD_EXISTS                     =   "Account already assigned to another user."
AUTH_PROVIDER_LOGIN_TO_ADD                   =   "The new login method will be assigned once you login to your account."
AUTH_PROVIDER_INVALID_LOGIN                  =   "No account exists."


messages = locals().keys()
for msg in messages:
    if msg == msg.upper():
        attr = "ASTAKOS_%s_MESSAGE" % msg
        settings_value = getattr(settings, attr, None)
        if settings_value:
            locals()[msg] = settings_value