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

import recaptcha.client.captcha as captcha

from django import forms
from django.utils.safestring import mark_safe
from django.utils import simplejson as json
from synnefo_branding.utils import render_to_string

from astakos.im import settings


class RecaptchaWidget(forms.Widget):
    """ A Widget which "renders" the output of captcha.displayhtml """
    def render(self, *args, **kwargs):
        conf = settings.RECAPTCHA_OPTIONS
        recaptcha_conf = ('<script type="text/javascript">'
                          'var RecaptchaOptions = %s'
                          '</script>') % json.dumps(conf)
        custom_widget_html = render_to_string("im/captcha.html",
                                              {'conf': 'Bob'})
        return mark_safe(
            recaptcha_conf +
            custom_widget_html +
            captcha.displayhtml(
                settings.RECAPTCHA_PUBLIC_KEY,
                use_ssl=settings.RECAPTCHA_USE_SSL))


class DummyWidget(forms.Widget):
    """
    A dummy Widget class for a placeholder input field which will
    be created by captcha.displayhtml

    """
    # make sure that labels are not displayed either
    is_hidden = True

    def render(self, *args, **kwargs):
        return ''
