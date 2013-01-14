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

ACCOUNT_AUTHENTICATION_FAILED           =   'Authenticate with this account failed.'
ACCOUNT_ALREADY_ACTIVE                  =   'This account is already active.'
ACCOUNT_PENDING_ACTIVATION              =   'Your account request is pending activation.'
ACCOUNT_PENDING_MODERATION              =   'Your account request is pending moderation.'
ACCOUNT_INACTIVE                        =   'Your account is disabled.'
ACCOUNT_RESEND_ACTIVATION               =   'It seems that an activation email has been sent to you, but you have not followed the activation link. <a href="%(send_activation_url)s">Resend activation email.</a>'
INACTIVE_ACCOUNT_CHANGE_EMAIL           =   ''.join([ACCOUNT_RESEND_ACTIVATION, ' Or <a href="%(signup_url)s">Send activation to a new email.</a>'])

ACCOUNT_PENDING_ACTIVATION_HELP         =   'An activation email has been sent to you. Make sure you check your spam folder, too.'

ACCOUNT_ACTIVATED                       =   'Congratulations. Your account has' + \
                                            ' been activated and you have been' + \
                                            ' automatically signed in.'
PASSWORD_RESET_DONE                     =   'An email with details on how to change your password has been sent. Please check your Inbox.'
PASSWORD_RESET_CONFIRM_DONE             =   'Your password has changed successfully. You can now login using your new password.'

ACCOUNT_RESEND_ACTIVATION_PROMPT        =   'Resend activation email'
ACCOUNT_USER_ACTIVATION_PENDING         =   'You have not followed the activation link'

ACCOUNT_UNKNOWN                         =   'It seems there is no account with those .'
TOKEN_UNKNOWN                           =   'There is no user matching this token.'

PROFILE_UPDATED                         =   'Your profile has been updated successfully.'
FEEDBACK_SENT                           =   'Thank you for your feedback. We will process it carefully.'
EMAIL_CHANGED                           =   'The email of your account changed successfully.'
EMAIL_CHANGE_REGISTERED                 =   'Your request for changing your email has been registered succefully. \
                                               A verification email at your new address is going to be sent.'

OBJECT_CREATED                          =   'The %(verbose_name)s was created successfully.'
USER_JOINED_GROUP                       =   'User %(realname)s joined the project.'
USER_LEFT_GROUP                         =   'User %(realname)s left the project.'
USER_MEMBERSHIP_REJECTED                =   'User\'s %(realname)s request to join the project has been rejected.'
MEMBER_REMOVED                          =   'User %(realname)s has been successfully removed from the project.'
BILLING_ERROR                           =   'Service response status: %(status)d'
LOGOUT_SUCCESS                          =   'Logged out from ~okeanos.'
LOGIN_SUCCESS                           =   'You are logged in to ~okeanos with your %s account.'
LOCAL_LOGIN_SUCCESS                     =   'You are logged in to your ~okeanos account.'

GENERIC_ERROR                           =   'Hmm... It seems something bad has happened, and we don\'t know the details right now. \
                                               Please contact the administrators by email for more details.'

MAX_INVITATION_NUMBER_REACHED   =           'You have reached the maximum amount of invitations for your account. No invitations left.'
GROUP_MAX_PARTICIPANT_NUMBER_REACHED    =   'This Group reached its maximum number of members. No other member can be added.'
PROJECT_MAX_PARTICIPANT_NUMBER_REACHED  =   'This Project reached its maximum number of members. No other member can be added.'
NO_APPROVAL_TERMS                       =   'There are no terms of service to approve.'
PENDING_EMAIL_CHANGE_REQUEST            =   'It seems there is already a pending request for an email change. ' + \
                                            'Submiting a new request to change your email will cancel all previous requests.'
OBJECT_CREATED_FAILED                   =   'The %(verbose_name)s creation failed: %(reason)s.'
GROUP_JOIN_FAILURE                      =   'Failed to join this Group.'
PROJECT_JOIN_FAILURE                    =   'Failed to join this Project.'
GROUPKIND_UNKNOWN                       =   'The kind of Project you specified does not exist.'
NOT_MEMBER                              =   'User is not a member of the Project.'
NOT_OWNER                               =   'User is not the Project\'s owner.'
OWNER_CANNOT_LEAVE_GROUP                =   'You are the owner of this Project. Owners can not leave their Projects.'

# Field validation fields
REQUIRED_FIELD                          =   'This field is required.'
EMAIL_USED                              =   'The email address you provided is already in use. Please provide a different email address.'
SHIBBOLETH_EMAIL_USED                   =   'This email is already associated with another shibboleth account.'
SHIBBOLETH_INACTIVE_ACC                 =   'This email is already associated with an account that is not yet activated. \
                                               If that is your account, you need to activate it before being able to \
                                               associate it with this shibboleth account.'
SHIBBOLETH_MISSING_EPPN = 'Your request is missing a unique ' + \
                          'token. This means your academic ' + \
                          'institution does not yet allow its users to log ' + \
                          'into %(domain)s with their academic ' + \
                          'credentials. Please contact %(contact_email)s' + \
                          ' for more information.'
SHIBBOLETH_MISSING_NAME                 =   'This request is missing the user name.'

SIGN_TERMS                              =   'Please, you need to \'Agree with the terms\' before proceeding.'
CAPTCHA_VALIDATION_ERR                  =   'You have not entered the correct words. Please try again.'
SUSPENDED_LOCAL_ACC                     =   'You can not login with your local credentials. This account does not have a local password. \
                                               Please try logging in using an external login provider (e.g.: twitter)'
UNUSABLE_PASSWORD                       =   'You can not use a local password for this account. Only external login providers are enabled.'
EMAIL_UNKNOWN                           =   'This email address doesn\'t have an associated user account. \
                                               Please make sure you have registered, before proceeding.'
INVITATION_EMAIL_EXISTS                 =   'There is already invitation for this email.'
INVITATION_CONSUMED_ERR                 =   'Invitation is used.'
UNKNOWN_USERS                           =   'Unknown users: %s'
UNIQUE_EMAIL_IS_ACTIVE_CONSTRAIN_ERR    =   'More than one account with the same email & \'is_active\' field. Error.'
INVALID_ACTIVATION_KEY                  =   'Invalid activation key.'
NEW_EMAIL_ADDR_RESERVED                 =   'The new email address you requested is already used by another account. Please provide a different one.'
EMAIL_RESERVED                          =   'Email: %(email)s is already reserved.'
NO_LOCAL_AUTH                           =   'Only external login providers are enabled for this acccount. You can not login with a local password.'
SWITCH_ACCOUNT_FAILURE                  =   'Account failed to switch. Invalid parameters.'
SWITCH_ACCOUNT_SUCCESS_WITH_PROVIDER    =   'Account failed to switch to %(provider)s.'
SWITCH_ACCOUNT_SUCCESS                  =   'Account successfully switched to %(provider)s.'

# Field help text
ADD_GROUP_MEMBERS_Q_HELP                =   'Add a comma separated list of user emails, eg. user1@user.com, user2@user.com'
ASTAKOSUSER_GROUPS_HELP                 =   'In addition to the permissions assigned manually, \
                                               this user will also get all permissions coming from his/her groups.'
EMAIL_CHANGE_NEW_ADDR_HELP              =   'Your old email address will be used, until you verify your new one.'

EMAIL_SEND_ERR                          =   'Failed to send %s.'
ADMIN_NOTIFICATION_SEND_ERR             =   EMAIL_SEND_ERR % 'admin notification'
VERIFICATION_SEND_ERR                   =   EMAIL_SEND_ERR % 'verification'
INVITATION_SEND_ERR                     =   EMAIL_SEND_ERR % 'invitation'
GREETING_SEND_ERR                       =   EMAIL_SEND_ERR % 'greeting'
FEEDBACK_SEND_ERR                       =   EMAIL_SEND_ERR % 'feedback'
CHANGE_EMAIL_SEND_ERR                   =   EMAIL_SEND_ERR % 'feedback'
NOTIFICATION_SEND_ERR                   =   EMAIL_SEND_ERR % 'notification'
DETAILED_NOTIFICATION_SEND_ERR          =   'Failed to send %(subject)s notification to %(recipients)s.'

MISSING_NEXT_PARAMETER                  =   'The next parameter is missing.'

INVITATION_SENT                         =   'Invitation sent to %(email)s.'
VERIFICATION_SENT                       =   'Your information has been submitted successfully. A verification email, with an activation link \
                                               has been sent to the email address you provided. Please follow the activation link on this \
                                               email to complete the registration process.'
SWITCH_ACCOUNT_LINK_SENT                =   'This email is already associated with a local account, and a verification email has been sent \
                                             to %(email)s. To complete the association process, go back to your Inbox and follow the link \
                                             inside the verification email.'
NOTIFICATION_SENT                       =   'Your request for an account has been submitted successfully, and is now pending approval. \
                                               You will be notified by email in the next few days. \
                                               Thanks for your interest in ~okeanos! The GRNET team.'
ACTIVATION_SENT                         =   'An email containing your activation link has been sent to your email address.'

REGISTRATION_COMPLETED                  =   'Your registration completed successfully. You can now login to your new account!'

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
MEMBER_NUMBER_LIMIT_REACHED             =   'You have reached the maximum number of members for this Project.'
MEMBER_JOIN_POLICY_CLOSED               =   'The Project\'s member join policy is closed.'
MEMBER_LEAVE_POLICY_CLOSED              =   'The project\'s member leave policy is closed.'
NOT_MEMBERSHIP_REQUEST                  =   'This is not a valid membership request.'
MEMBERSHIP_REQUEST_EXISTS               =   'The membership request already exists.'
NO_APPLICANT                            =   'Project application requires an applicant. None found.'
INVALID_PROJECT_START_DATE              =   'Project start date should be equal or greater than the current date'
INVALID_PROJECT_END_DATE                =   'Project end date should be equal or greater than than the current date'
INCONSISTENT_PROJECT_DATES              =   'Project end date should be greater than the project start date'
ADD_PROJECT_MEMBERS_Q_HELP              =   'Add a comma separated list of user emails, eg. user1@user.com, user2@user.com'
MISSING_IDENTIFIER                      =   'Missing identifier.'
UNKNOWN_USER_ID                         =   'There is no user identified by %s.'
UNKNOWN_PROJECT_APPLICATION_ID          =   'There is no project application identified by %s.'
UNKNOWN_PROJECT_ID                      =   'There is no project identified by %s.'
UNKNOWN_IDENTIFIER                      =   'Unknown identifier.'
PENDING_MEMBERSHIP_LEAVE                =   'Your request is pending moderation by the Project owner.'
USER_JOINED_PROJECT                     =   '%(realname)s has joined the Project.'
USER_LEFT_PROJECT                       =   '%(realname)s has left the Project.'
USER_JOIN_REQUEST_SUBMITED              =   'Join request submitted.'

# Auth providers messages
AUTH_PROVIDER_NOT_ACTIVE                     =   "'%(provider)s' is disabled."
AUTH_PROVIDER_NOT_ACTIVE_FOR_LOGIN           =   "Login using '%(provider)s' is disabled."
AUTH_PROVIDER_NOT_ACTIVE_FOR_USER            =   "You cannot login using '%(provider)s'."
AUTH_PROVIDER_NOT_ACTIVE_FOR_CREATE          =   "Signup using '%(provider)s' is disabled."
AUTH_PROVIDER_NOT_ACTIVE_FOR_ADD             =   "You cannot add %(provider)s login method."
AUTH_PROVIDER_ADDED                          =   "New login method added."
AUTH_PROVIDER_ADD_FAILED                     =   "Failed to add new login method."
AUTH_PROVIDER_ADD_EXISTS                     =   "Account already assigned to another user."
AUTH_PROVIDER_LOGIN_TO_ADD                   =   "The new login method will be assigned once you login to your account."
AUTH_PROVIDER_INVALID_LOGIN                  =   "No account exists."
AUTH_PROVIDER_REQUIRED                       =   "%(provider)s login method is required. Add one from your profile page."
AUTH_PROVIDER_CANNOT_CHANGE_PASSWORD         =   "Changing password is not supported."

EXISTING_EMAIL_THIRD_PARTY_NOTIFICATION      =   "You can add '%s' login method to your existing account from your " \
                                                 " <a href='%s'>profile page</a>"

messages = locals().keys()
for msg in messages:
    if msg == msg.upper():
        attr = "ASTAKOS_%s_MESSAGE" % msg
        settings_value = getattr(settings, attr, None)
        if settings_value:
            locals()[msg] = settings_value
