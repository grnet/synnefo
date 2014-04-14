# -*- coding: utf-8 -*-

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


def strbigdec(bignum, nr_lsd=12):
    all_digits = str(bignum)
    ms_digits = all_digits[:-nr_lsd]
    if not ms_digits:
        return all_digits

    if len(ms_digits.rstrip('0')) == 1:
        approx = ''
    else:
        approx = '~'

    ls_digits = all_digits[-nr_lsd:]
    ls_num = int(ls_digits)
    ms_num = bignum - ls_num
    if ls_num:
        display = "[%s%1.0e]%+d" % (approx, ms_num, ls_num)
    else:
        display = "[%s%1.0e]" % (approx, ms_num)
    return display
