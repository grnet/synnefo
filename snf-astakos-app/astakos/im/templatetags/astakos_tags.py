from django import template
from django.core.urlresolvers import reverse, resolve
from django.conf import settings

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
                content += '<div class="msg %s">%s</div>' % (msg.tags, msg.message)

            content += '<a href="#" title="close" class="close">X</a>'
            content += '</div>'
            context.render_context[self] = content

        return context.render_context[self]
