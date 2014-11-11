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
