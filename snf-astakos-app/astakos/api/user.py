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

import logging

from functools import wraps, partial

from django.views.decorators.csrf import csrf_exempt
from django import http
from django.db import transaction
from django.utils import simplejson as json
from django.forms.models import model_to_dict
from django.core.validators import validate_email, ValidationError

from snf_django.lib import api
from snf_django.lib.api import faults

from .util import (
    get_uuid_displayname_catalogs as get_uuid_displayname_catalogs_util,
    send_feedback as send_feedback_util,
    user_from_token)

from astakos.im import settings
from astakos.admin import stats
from astakos.im.models import AstakosUser, get_latest_terms
from astakos.im.auth import make_local_user
from astakos.im import activation_backends

ADMIN_GROUPS = settings.ADMIN_API_PERMITTED_GROUPS

activation_backend = activation_backends.get_backend()

logger = logging.getLogger(__name__)

@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False,
                logger=logger)
@user_from_token  # Authenticate user!!
def get_uuid_displayname_catalogs(request):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)

    return get_uuid_displayname_catalogs_util(request)


@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False,
                logger=logger)
@user_from_token  # Authenticate user!!
def send_feedback(request, email_template_name='im/feedback_mail.txt'):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)

    return send_feedback_util(request, email_template_name)


# API ADMIN UTILS AND ENDPOINTS

def user_api_method(http_method):
    """
    Common decorator for user admin api views.
    """
    def wrapper(func):
        @api.api_method(http_method=http_method, user_required=True,
                        token_required=True, logger=logger,
                        serializations=['json'])
        @api.user_in_groups(permitted_groups=ADMIN_GROUPS,
                            logger=logger)
        @wraps(func)
        def method(*args, **kwargs):
            return func(*args, **kwargs)

        return method
    return wrapper


def user_to_dict(user, detail=True):
    user_fields = ['first_name', 'last_name', 'email']
    date_fields = ['date_joined', 'moderated_at', 'verified_at',
                   'auth_token_expires']
    status_fields = ['is_active', 'is_rejected', 'deactivated_reason',
                     'accepted_policy', 'rejected_reason']
    if not detail:
        fields = user_fields
        date_fields = []
    d = model_to_dict(user, fields=user_fields + status_fields)
    d['id'] = user.uuid
    for date_field in date_fields:
        val = getattr(user, date_field)
        if val:
            d[date_field] = api.utils.isoformat(getattr(user, date_field))
        else:
            d[date_field] = None

    methods = d['authentication_methods'] = []
    d['roles'] = list(user.groups.values_list("name", flat=True))

    for provider in user.auth_providers.filter():
        method_fields = ['identifier', 'active', 'affiliation']
        method = model_to_dict(provider, fields=method_fields)
        method['backend'] = provider.auth_backend
        method['metadata'] = provider.info
        if provider.auth_backend == 'astakos':
            method['identifier'] = user.email
        methods.append(method)

    return d


def users_demux(request):
    if request.method == 'GET':
        return users_list(request)
    elif request.method == 'POST':
        return users_create(request)
    else:
        return api.api_method_not_allowed(request)


def user_demux(request, user_id):
    if request.method == 'GET':
        return user_detail(request, user_id)
    elif request.method == 'PUT':
        return user_update(request, user_id)
    else:
        return api.api_method_not_allowed(request)


@user_api_method('GET')
def users_list(request, action='list', detail=False):
    logger.debug('users_list detail=%s', detail)
    users = AstakosUser.objects.filter()
    dict_func = partial(user_to_dict, detail=detail)
    users_dicts = map(dict_func, users)
    data = json.dumps({'users': users_dicts})
    return http.HttpResponse(data, status=200,
                             content_type='application/json')


@user_api_method('POST')
@transaction.commit_on_success
def users_create(request):
    user_id = request.user_uniq
    req = api.utils.get_json_body(request)
    logger.info('users_create: %s request: %s', user_id, req)

    user_data = req.get('user', {})
    email = user_data.get('username', None)

    first_name = user_data.get('first_name', None)
    last_name = user_data.get('last_name', None)
    affiliation = user_data.get('affiliation', None)
    password = user_data.get('password', None)
    metadata = user_data.get('metadata', {})

    password_gen = AstakosUser.objects.make_random_password
    if not password:
        password = password_gen()

    try:
        validate_email(email)
    except ValidationError:
        raise faults.BadRequest("Invalid username (email format required)")

    if AstakosUser.objects.verified_user_exists(email):
        raise faults.Conflict("User '%s' already exists" % email)

    if not first_name:
        raise faults.BadRequest("Invalid first_name")

    if not last_name:
        raise faults.BadRequest("Invalid last_name")

    has_signed_terms = not(get_latest_terms())

    try:
        user = make_local_user(email, first_name=first_name,
                               last_name=last_name, password=password,
                               has_signed_terms=has_signed_terms)
        if metadata:
            # we expect a unique local auth provider for the user
            provider = user.auth_providers.get()
            provider.info = metadata
            provider.affiliation = affiliation
            provider.save()

        user = AstakosUser.objects.get(pk=user.pk)
        code = user.verification_code
        ver_res = activation_backend.handle_verification(user, code)
        if ver_res.is_error():
            raise Exception(ver_res.message)
        mod_res = activation_backend.handle_moderation(user, accept=True)
        if mod_res.is_error():
            raise Exception(ver_res.message)

    except Exception, e:
        raise faults.BadRequest(e.message)

    user_data = {
        'id': user.uuid,
        'password': password,
        'auth_token': user.auth_token,
    }
    data = json.dumps({'user': user_data})
    return http.HttpResponse(data, status=200, content_type='application/json')


@user_api_method('POST')
@transaction.commit_on_success
def user_action(request, user_id):
    admin_id = request.user_uniq
    req = api.utils.get_json_body(request)
    logger.info('user_action: %s user: %s request: %s', admin_id, user_id, req)
    if 'activate' in req:
        try:
            user = AstakosUser.objects.get(uuid=user_id)
        except AstakosUser.DoesNotExist:
            raise faults.ItemNotFound("User not found")

        activation_backend.activate_user(user)

        user = AstakosUser.objects.get(uuid=user_id)
        user_data = {
            'id': user.uuid,
            'is_active': user.is_active
        }
        data = json.dumps({'user': user_data})
        return http.HttpResponse(data, status=200,
                                 content_type='application/json')
    if 'deactivate' in req:
        try:
            user = AstakosUser.objects.get(uuid=user_id)
        except AstakosUser.DoesNotExist:
            raise faults.ItemNotFound("User not found")

        activation_backend.deactivate_user(
            user, reason=req['deactivate'].get('reason', None))

        user = AstakosUser.objects.get(uuid=user_id)
        user_data = {
            'id': user.uuid,
            'is_active': user.is_active
        }
        data = json.dumps({'user': user_data})
        return http.HttpResponse(data, status=200,
                                 content_type='application/json')

    if 'renewToken' in req:
        try:
            user = AstakosUser.objects.get(uuid=user_id)
        except AstakosUser.DoesNotExist:
            raise faults.ItemNotFound("User not found")
        user.renew_token()
        user.save()
        user_data = {
            'id': user.uuid,
            'auth_token': user.auth_token,
        }
        data = json.dumps({'user': user_data})
        return http.HttpResponse(data, status=200,
                                 content_type='application/json')

    raise faults.BadRequest("Invalid action")


@user_api_method('PUT')
@transaction.commit_on_success
def user_update(request, user_id):
    admin_id = request.user_uniq
    req = api.utils.get_json_body(request)
    logger.info('user_update: %s user: %s request: %s', admin_id, user_id, req)

    user_data = req.get('user', {})

    try:
        user = AstakosUser.objects.get(uuid=user_id)
    except AstakosUser.DoesNotExist:
        raise faults.ItemNotFound("User not found")

    email = user_data.get('username', None)
    first_name = user_data.get('first_name', None)
    last_name = user_data.get('last_name', None)
    affiliation = user_data.get('affiliation', None)
    password = user_data.get('password', None)
    metadata = user_data.get('metadata', {})

    if 'password' in user_data:
        user.set_password(password)

    if 'username' in user_data:
        try:
            validate_email(email)
        except ValidationError:
            raise faults.BadRequest("Invalid username (email format required)")

        if AstakosUser.objects.verified_user_exists(email):
            raise faults.Conflict("User '%s' already exists" % email)

        user.email = email

    if 'first_name' in user_data:
        user.first_name = first_name

    if 'last_name' in user_data:
        user.last_name = last_name

    try:
        user.save()
        if 'metadata' in user_data:
            provider = user.auth_providers.get(auth_backend="astakos")
            provider.info = metadata
            if affiliation in user_data:
                provider.affiliation = affiliation
            provider.save()

    except Exception, e:
        raise faults.BadRequest(e.message)

    data = json.dumps({'user': user_to_dict(user)})
    return http.HttpResponse(data, status=200, content_type='application/json')


@user_api_method('GET')
def user_detail(request, user_id):
    admin_id = request.user_uniq
    logger.info('user_detail: %s user: %s', admin_id, user_id)
    try:
        user = AstakosUser.objects.get(uuid=user_id)
    except AstakosUser.DoesNotExist:
        raise faults.ItemNotFound("User not found")

    user_data = user_to_dict(user, detail=True)
    data = json.dumps({'user': user_data})
    return http.HttpResponse(data, status=200, content_type='application/json')
