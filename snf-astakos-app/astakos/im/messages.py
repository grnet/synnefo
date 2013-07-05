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
import astakos.im.settings as astakos_settings


LOGGED_IN_WARNING = 'It seems that you are already logged in.'
ACCOUNT_ALREADY_VERIFIED = 'This account is already verified.'
ACCOUNT_ALREADY_MODERATED = 'This account is already moderated.'
ACCOUNT_ALREADY_ACTIVE = 'This account is already active.'
ACCOUNT_REJECTED = 'This account has been rejected.'
ACCOUNT_NOT_ACTIVE = 'User account is not active.'
ACCOUNT_NOT_MODERATED = 'User account is not moderated.'
ACCOUNT_NOT_VERIFIED = 'User account does not have a verified email address.'
ACCOUNT_RESEND_ACTIVATION = (
    'It seems that an activation email has been sent to you, but you have '
    'not followed the activation link. '
    '<a href="%(send_activation_url)s">Resend activation email.</a>')
INACTIVE_ACCOUNT_CHANGE_EMAIL = ''.join(
    [ACCOUNT_RESEND_ACTIVATION,
     ' Or <a href="%(signup_url)s">Send activation to a new email.</a>'])

ACCOUNT_PENDING_ACTIVATION_HELP = (
    'An activation email has been sent to you. Make sure you check your '
    'spam folder, too.')

ACCOUNT_ACTIVATED = 'Congratulations. Your account has' + \
    ' been activated. You are now logged in.'
ACCOUNT_DEACTIVATED = 'Your account is inactive'
PASSWORD_RESET_DONE = (
    'An email with details on how to change your password has been sent. '
    'Please check your Inbox.')
PASSWORD_RESET_CONFIRM_DONE = (
    'Your password has changed successfully. You '
    'can now login using your new password.')
PASSWORD_CHANGED = 'Your new password was set successfully.'

ACCOUNT_RESEND_ACTIVATION = 'Resend activation email'
ACCOUNT_USER_ACTIVATION_PENDING = 'You have not followed the activation link'

ACCOUNT_UNKNOWN = 'There is no such account.'
TOKEN_UNKNOWN = 'There is no user matching this authentication token.'
TOKEN_UPDATED = 'Your authentication token has been updated successfully.'

PROFILE_UPDATED = 'Your profile has been updated successfully.'
FEEDBACK_SENT = (
    'Thank you for contacting us. We will process your message carefully '
    'and get back to you.')
EMAIL_CHANGED = 'The email of your account changed successfully.'
EMAIL_CHANGE_REGISTERED = (
    'Your request for changing your email has been registered successfully. '
    'A verification email will be sent to your new address.')

OBJECT_CREATED = 'The %(verbose_name)s was created successfully.'
USER_MEMBERSHIP_REJECTED = (
    'Request by %s to join the project has been rejected.')
BILLING_ERROR = 'Service response status: %(status)d'

GENERIC_ERROR = (
    'Hmm... It seems something bad has happened, and we don\'t know the '
    'details right now. Please contact the administrators by email for '
    'more details.')

MAX_INVITATION_NUMBER_REACHED = (
    'You have reached the maximum amount of invitations for your account. '
    'No invitations left.')
GROUP_MAX_PARTICIPANT_NUMBER_REACHED = (
    'This Group reached its maximum number of members. No other member can '
    'be added.')
PROJECT_MAX_PARTICIPANT_NUMBER_REACHED = (
    'This Project reached its maximum number of members. No other member '
    'can be added.')
NO_APPROVAL_TERMS = 'There are no terms of service to approve.'
PENDING_EMAIL_CHANGE_REQUEST = (
    'It seems there is already a pending request for an email change. '
    'Submitting a new request to change your email will cancel all previous '
    'requests.')
OBJECT_CREATED_FAILED = 'The %(verbose_name)s creation failed: %(reason)s.'
GROUP_JOIN_FAILURE = 'Failed to join this Group.'
PROJECT_JOIN_FAILURE = 'Failed to join this Project.'
GROUPKIND_UNKNOWN = 'The kind of Project you specified does not exist.'
NOT_MEMBER = 'User is not a member of the Project.'
NOT_OWNER = 'User is not the Project\'s owner.'
OWNER_CANNOT_LEAVE_GROUP = (
    'You are the owner of this Project. Owners can not leave their Projects.')

# Field validation fields
REQUIRED_FIELD = 'This field is required.'
EMAIL_USED = 'There is already an account with this email address.'
SHIBBOLETH_EMAIL_USED = (
    'This email is already associated with another shibboleth account.')
SHIBBOLETH_INACTIVE_ACC = (
    'This email is already associated with an account that is not '
    'yet activated. '
    'If that is your account, you need to activate it before being able to '
    'associate it with this shibboleth account.')
SHIBBOLETH_MISSING_EPPN = (
    'Your request is missing a unique ' +
    'token. This means your academic ' +
    'institution does not yet allow its users to log ' +
    'into %(domain)s with their academic ' +
    'account. Please contact %(contact_email)s' +
    ' for more information.')
SHIBBOLETH_MISSING_NAME = 'This request is missing the user name.'

SIGN_TERMS = "Please, you need to 'Agree with the terms' before proceeding."
CAPTCHA_VALIDATION_ERR = (
    "You have not entered the correct words. Please try again."
)
SUSPENDED_LOCAL_ACC = (
    "This account does not have a local password. "
    "Please try logging in using an external login provider (e.g.: twitter)"
)
EMAIL_UNKNOWN = (
    "This email address doesn't have an associated user account. "
    "Please make sure you have registered, before proceeding."
)
INVITATION_EMAIL_EXISTS = "An invitation has already been sent to this email."
INVITATION_CONSUMED_ERR = "The invitation has already been used."
UNKNOWN_USERS = "Unknown users: %s"
UNIQUE_EMAIL_IS_ACTIVE_CONSTRAIN_ERR = (
    "More than one account with the same email & 'is_active' field. Error."
)
INVALID_ACTIVATION_KEY = "Invalid activation key."
NEW_EMAIL_ADDR_RESERVED = (
    "The new email address you requested is already used by another account. "
    "Please provide a different one."
)
EMAIL_RESERVED = "Email: %(email)s is already reserved."
NO_LOCAL_AUTH = (
    "Only external login providers are enabled for this account. "
    "You can not login with a local password."
)
SWITCH_ACCOUNT_FAILURE = "Account failed to switch. Invalid parameters."
SWITCH_ACCOUNT_SUCCESS_WITH_PROVIDER = (
    "Account failed to switch to %(provider)s."
)
SWITCH_ACCOUNT_SUCCESS = (
    "Account successfully switched to %(provider)s."
)

# Field help text
ADD_GROUP_MEMBERS_Q_HELP = (
    'Add a comma separated list of user emails, eg. user1@user.com, '
    'user2@user.com')
ASTAKOSUSER_GROUPS_HELP = (
    'In addition to the permissions assigned manually, '
    'this user will also get all permissions coming from his/her groups.')

EMAIL_SEND_ERR = 'Failed to send %s.'
ADMIN_NOTIFICATION_SEND_ERR = EMAIL_SEND_ERR % 'admin notification'
VERIFICATION_SEND_ERR = EMAIL_SEND_ERR % 'verification'
INVITATION_SEND_ERR = EMAIL_SEND_ERR % 'invitation'
GREETING_SEND_ERR = EMAIL_SEND_ERR % 'greeting'
FEEDBACK_SEND_ERR = EMAIL_SEND_ERR % 'feedback'
CHANGE_EMAIL_SEND_ERR = EMAIL_SEND_ERR % 'email change'
NOTIFICATION_SEND_ERR = EMAIL_SEND_ERR % 'notification'
DETAILED_NOTIFICATION_SEND_ERR = (
    'Failed to send %(subject)s notification to %(recipients)s.')

MISSING_NEXT_PARAMETER = 'The next parameter is missing.'

INVITATION_SENT = 'Invitation sent to %(email)s.'
VERIFICATION_SENT = (
    'Your information has been submitted successfully. A verification email, '
    'with an activation link has been sent to the email address you provided. '
    'Please follow the activation link on this email to complete the '
    'registration process.')
VERIFICATION_FAILED = 'Email verification process failed.'
SWITCH_ACCOUNT_LINK_SENT = (
    'This email is already associated with a local account, '
    'and a verification email has been sent to %(email)s. To complete '
    'the association process, go back to your Inbox and follow the link '
    'inside the verification email.')
NOTIFICATION_SENT = (
    'Your request for an account has been submitted successfully, and is '
    'now pending approval. You will be notified by email in the next few '
    'days. Thanks for your interest!')
ACTIVATION_SENT = (
    'An email containing your activation link has been sent to your '
    'email address.')

REGISTRATION_COMPLETED = (
    'Your registration completed successfully. You can now login to your '
    'new account!')

NO_RESPONSE = 'There is no response.'
NOT_ALLOWED_NEXT_PARAM = 'Not allowed next parameter.'
MISSING_KEY_PARAMETER = 'Missing key parameter.'
INVALID_KEY_PARAMETER = 'Invalid key.'
DOMAIN_VALUE_ERR = 'Enter a valid domain.'
QH_SYNC_ERROR = 'Failed to get synchronized with quotaholder.'
UNIQUE_PROJECT_NAME_CONSTRAIN_ERR = (
    'The project name (as specified in its application\'s definition) must '
    'be unique among all active projects.')
INVALID_PROJECT = 'Project %(id)s is invalid.'
NOT_ALIVE_PROJECT = 'Project %(id)s is not alive.'
NOT_SUSPENDED_PROJECT = 'Project %(id)s is not suspended.'
NOT_ALLOWED = 'You do not have the permissions to perform this action.'
MEMBER_NUMBER_LIMIT_REACHED = (
    'You have reached the maximum number of members for this Project.')
MEMBER_JOIN_POLICY_CLOSED = 'The Project\'s member join policy is closed.'
MEMBER_LEAVE_POLICY_CLOSED = 'The project\'s member leave policy is closed.'
NOT_MEMBERSHIP_REQUEST = 'This is not a valid membership request.'
NOT_ACCEPTED_MEMBERSHIP = 'This is not an accepted membership.'
MEMBERSHIP_REQUEST_EXISTS = 'The membership request already exists.'
NO_APPLICANT = (
    'Project application requires at least one applicant. None found.')
INVALID_PROJECT_START_DATE = (
    'Project start date should be equal or greater than the current date.')
INVALID_PROJECT_END_DATE = (
    'Project end date should be equal or greater than than the current date.')
INCONSISTENT_PROJECT_DATES = (
    'Project end date should be greater than the project start date.')
ADD_PROJECT_MEMBERS_Q_HELP = (
    'Add a comma separated list of user emails, eg. user1@user.com, '
    'user2@user.com')
ADD_PROJECT_MEMBERS_Q_PLACEHOLDER = 'user1@user.com, user2@user.com'
MISSING_IDENTIFIER = 'Missing identifier.'
UNKNOWN_USER_ID = 'There is no user identified by %s.'
UNKNOWN_PROJECT_APPLICATION_ID = (
    'There is no project application identified by %s.')
UNKNOWN_PROJECT_ID = 'There is no project identified by %s.'
UNKNOWN_IDENTIFIER = 'Unknown identifier.'
PENDING_MEMBERSHIP_LEAVE = (
    'Your request is pending moderation by the Project owner.')
USER_MEMBERSHIP_ACCEPTED = '%s has been accepted in the project.'
USER_MEMBERSHIP_REMOVED = '%s has been removed from the project.'
USER_LEFT_PROJECT = 'You have left the project.'
USER_LEAVE_REQUEST_SUBMITTED = (
    'Your request to leave the project has been submitted successfully.')
USER_JOIN_REQUEST_SUBMITTED = (
    'Your request to join the project has been submitted successfully.')
USER_JOINED_PROJECT = 'You have joined the project.'
USER_REQUEST_CANCELLED = 'Your request to join the project has been cancelled.'
APPLICATION_CANNOT_APPROVE = "Cannot approve application %s in state '%s'"
APPLICATION_CANNOT_DENY = "Cannot deny application %s in state '%s'"
APPLICATION_CANNOT_DISMISS = "Cannot dismiss application %s in state '%s'"
APPLICATION_CANNOT_CANCEL = "Cannot cancel application %s in state '%s'"
APPLICATION_CANCELLED = "Your project application has been cancelled."

REACHED_PENDING_APPLICATION_LIMIT = ("You have reached the maximum number "
                                     "of pending project applications: %s.")

PENDING_APPLICATION_LIMIT_ADD = \
    ("You are not allowed to create a new project "
     "because you have reached the maximum [%s] for "
     "pending project applications. "
     "Consider cancelling any unnecessary ones.")

PENDING_APPLICATION_LIMIT_MODIFY = \
    ("You are not allowed to modify this project "
     "because you have reached the maximum [%s] for "
     "pending project applications. "
     "Consider cancelling any unnecessary ones.")

# Auth providers messages
AUTH_PROVIDER_LOGIN_SUCCESS = "Logged in successfully, using {method_prompt}."
AUTH_PROVIDER_LOGOUT_SUCCESS = "Logged out successfully."
AUTH_PROVIDER_LOGOUT_SUCCESS_EXTRA = (
    "You may still be logged in at {title} though. "
    "Consider logging out from there too.")
AUTH_PROVIDER_NOT_ACTIVE = "'{method_prompt}' is disabled."
AUTH_PROVIDER_ADD_DISABLED = "{method_prompt} is disabled for your account."
AUTH_PROVIDER_NOT_ACTIVE_FOR_USER = "You cannot login using '{method_prompt}'."
AUTH_PROVIDER_NOT_ACTIVE_FOR_CREATE = (
    "Sign up using '{method_prompt}' is disabled.")
AUTH_PROVIDER_NOT_ACTIVE_FOR_ADD = "You cannot add {method_prompt}."
AUTH_PROVIDER_ADDED = "{method_prompt} enabled for this account."
AUTH_PROVIDER_SWITCHED = "{method_prompt} changed for this account."
AUTH_PROVIDER_REMOVED = "{method_prompt} removed for this account."
AUTH_PROVIDER_ADD_FAILED = "Failed to add {method_prompt}."
AUTH_PROVIDER_ADD_EXISTS = (
    "It seems that this '{method_prompt}' is already in use by "
    "another account.")
AUTH_PROVIDER_LOGIN_TO_ADD = (
    "The new login method will be assigned once you login to your account.")
AUTH_PROVIDER_INVALID_LOGIN = "No account exists."
AUTH_PROVIDER_REQUIRED = (
    "{method_prompt} is required. Add one from your profile page.")
AUTH_PROVIDER_CANNOT_CHANGE_PASSWORD = "Changing password is not supported."
AUTH_PROVIDER_SIGNUP_FROM_LOGIN = None
AUTH_PROVIDER_UNUSABLE_PASSWORD = (
    '{method_prompt} is not enabled'
    ' for your account. You can access your account by logging in with'
    ' {available_methods_links}.')
AUTH_PROVIDER_LOGIN_DISABLED = AUTH_PROVIDER_UNUSABLE_PASSWORD
AUTH_PROVIDER_SIGNUP_FROM_LOGIN = ''
AUTH_PROVIDER_AUTHENTICATION_FAILED = (
    'Authentication with this account failed.')


AUTH_PROVIDER_PENDING_REGISTRATION = '''A pending registration exists for
{title} account {username}. The email used for the registration is
{user_email}. If you decide to procceed with the signup process once again,
all pending registrations will be deleted.'''

AUTH_PROVIDER_PENDING_RESEND_ACTIVATION = (
    '<a href="{resend_activation_url}">Click here to resend activation '
    'email.</a>')
AUTH_PROVIDER_PENDING_MODERATION = (
    'Your account request is pending moderation.')
AUTH_PROVIDER_PENDING_ACTIVATION = (
    'Your account request is pending activation.')
AUTH_PROVIDER_ACCOUNT_INACTIVE = 'Your account is disabled.'

AUTH_PROVIDER_ADD_TO_EXISTING_ACCOUNT = (
    "You can add {method_prompt} to your existing account from your "
    " <a href='{profile_url}'>profile page</a>")

# Email subjects
_SITENAME = astakos_settings.SITENAME
INVITATION_EMAIL_SUBJECT = 'Invitation to %s' % _SITENAME
GREETING_EMAIL_SUBJECT = 'Welcome to %s' % _SITENAME
FEEDBACK_EMAIL_SUBJECT = 'Feedback from %s' % _SITENAME
VERIFICATION_EMAIL_SUBJECT = '%s account activation is needed' % _SITENAME
ACCOUNT_CREATION_SUBJECT = '%s account created (%%(user)s)' % _SITENAME
HELPDESK_NOTIFICATION_EMAIL_SUBJECT = \
    '%s account activated (%%(user)s)' % _SITENAME
EMAIL_CHANGE_EMAIL_SUBJECT = 'Email change on %s ' % _SITENAME
PASSWORD_RESET_EMAIL_SUBJECT = 'Password reset on %s ' % _SITENAME
PROJECT_CREATION_SUBJECT = \
    '%s project application created (%%(name)s)' % _SITENAME
PROJECT_APPROVED_SUBJECT = \
    '%s project application approved (%%(name)s)' % _SITENAME
PROJECT_DENIED_SUBJECT = \
    '%s project application denied (%%(name)s)' % _SITENAME
PROJECT_TERMINATION_SUBJECT = \
    '%s project terminated (%%(name)s)' % _SITENAME
PROJECT_SUSPENSION_SUBJECT = \
    '%s project suspended (%%(name)s)' % _SITENAME
PROJECT_MEMBERSHIP_CHANGE_SUBJECT = \
    '%s project membership changed (%%(name)s)' % _SITENAME
PROJECT_MEMBERSHIP_ENROLL_SUBJECT = \
    '%s project enrollment (%%(name)s)' % _SITENAME
PROJECT_MEMBERSHIP_REQUEST_SUBJECT = \
    '%s project membership request (%%(name)s)' % _SITENAME
PROJECT_MEMBERSHIP_LEAVE_REQUEST_SUBJECT = \
    '%s project membership leave request (%%(name)s)' % _SITENAME


messages = locals().keys()
for msg in messages:
    if msg == msg.upper():
        attr = "ASTAKOS_%s_MESSAGE" % msg
        settings_value = getattr(settings, attr, None)
        if settings_value:
            locals()[msg] = settings_value
