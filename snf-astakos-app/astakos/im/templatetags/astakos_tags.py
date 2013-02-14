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

import urllib

from inspect import getargspec

from django import template
from django.core.urlresolvers import resolve
from django.conf import settings
from django.template import TemplateSyntaxError, Variable

register = template.Library()

MESSAGES_VIEWS_MAP = getattr(settings, 'ASTAKOS_MESSAGES_VIEWS_MAP', {
    'astakos.im.views.index': 'LOGIN_MESSAGES',
    'astakos.im.views.logout': 'LOGIN_MESSAGES',
    'astakos.im.views.login': 'LOGIN_MESSAGES',
    'astakos.im.views.signup': 'SIGNUP_MESSAGES',
    'astakos.im.views.edit_profile': 'PROFILE_MESSAGES',
    'astakos.im.views.change_password': 'PROFILE_MESSAGES',
    'astakos.im.views.invite': 'PROFILE_MESSAGES',
    'astakos.im.views.feedback': 'PROFILE_MESSAGES',
})


# helper tag decorator
# https://github.com/djblets/djblets/blob/master/djblets/util/decorators.py#L96
def basictag(takes_context=False):
    """
    A decorator similar to Django's @register.simple_tag that optionally
    takes a context parameter. This condenses many tag implementations down
    to a few lines of code.

    Example:
        @register.tag
        @basictag(takes_context=True)
        def printuser(context):
            return context['user']
    """
    class BasicTagNode(template.Node):
        def __init__(self, take_context, tag_name, tag_func, args):
            self.takes_context = takes_context
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.args = args

        def render(self, context):
            args = [Variable(var).resolve(context) for var in self.args]

            if self.takes_context:
                return self.tag_func(context, *args)
            else:
                return self.tag_func(*args)

    def basictag_func(tag_func):
        def _setup_tag(parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            del(bits[0])

            params, xx, xxx, defaults = getargspec(tag_func)
            max_args = len(params)

            if takes_context:
                if params[0] == 'context':
                    max_args -= 1 # Ignore context
                else:
                    raise TemplateSyntaxError, \
                        "Any tag function decorated with takes_context=True " \
                        "must have a first argument of 'context'"

            min_args = max_args - len(defaults or [])

            if not min_args <= len(bits) <= max_args:
                if min_args == max_args:
                    raise TemplateSyntaxError, \
                        "%r tag takes %d arguments." % (tag_name, min_args)
                else:
                    raise TemplateSyntaxError, \
                        "%r tag takes %d to %d arguments, got %d." % \
                        (tag_name, min_args, max_args, len(bits))

            return BasicTagNode(takes_context, tag_name, tag_func, bits)

        _setup_tag.__name__ = tag_func.__name__
        _setup_tag.__doc__ = tag_func.__doc__
        _setup_tag.__dict__.update(tag_func.__dict__)
        return _setup_tag

    return basictag_func


@register.tag(name='display_messages')
def display_messages(parser, token):
    return MessagesNode()


class DummyMessage(object):
    def __init__(self, type, msg):
        self.message = msg
        self.tags = type

    def __repr__(self):
        return "%s: %s" % (self.tags, self.message)


class MessagesNode(template.Node):

    def get_view_messages(self, context):
        messages = list(context['GLOBAL_MESSAGES'])
        try:
            view = resolve(context['request'].get_full_path())[0]
            view_name = "%s.%s" % (view.__module__, view.func_name)
            messages += context[MESSAGES_VIEWS_MAP.get(view_name)]
            return messages
        except Exception, e:
            return messages

    def render(self, context):
        if self not in context.render_context:
            messages = list(context['messages'])
            if context['EXTRA_MESSAGES_SET']:
                view_messages = self.get_view_messages(context)
                for msg_object in view_messages:
                    messages.append(DummyMessage(msg_object[0], msg_object[1]))

            if not messages:
                return ""

            cls = messages[-1].tags
            content = '<div class="top-msg active %s">' % cls
            for msg in messages:
                content += '<div class="msg %s">%s</div>' % (
                    msg.tags, msg.message)

            content += '<a href="#" title="close" class="close">X</a>'
            content += '</div>'
            context.render_context[self] = content

        return context.render_context[self]


@register.simple_tag
def get_grant_value(rname, form):
    grants = form.instance.grants
    service_name, resource_name = rname.split('.',1)
    try:
        return form.instance.projectresourcegrant_set.get(resource__name=resource_name,
                                                           resource__service__name=service_name).member_capacity
    except:
        return ''

@register.tag(name="provider_login_url")
@basictag(takes_context=True)
def provider_login_url(context, provider, from_login=False):
    request = context['request'].REQUEST
    next = request.get('next', None)
    code = request.get('code', None)
    key = request.get('key', None)

    attrs = {}
    if next:
        attrs['next'] = next
    if code:
        attrs['code'] = code
    if key:
        attrs['key'] = key
    if from_login:
        attrs['from_login'] = 1

    url = provider.add_url

    joinchar = "?"
    if "?" in url:
        joinchar = "&"

    return "%s%s%s" % (provider.add_url, joinchar, urllib.urlencode(attrs))

