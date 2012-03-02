#!/bin/bash
#
#
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
#

set -e

rm -rf env
virtualenv --no-site-packages -ppython2.6 env
source env/bin/activate
export PIP_DOWNLOAD_CACHE=/tmp/.pip_cache
pip install -r requirements.pip

cd snf-common
rm -rf build dist
python setup.py install
cd ../snf-cyclades-app
rm -rf build dist
python setup.py install
cd ../snf-cyclades-gtools
rm -rf build dist
python setup.py install


cd ../env
# avoid vncauthproxy errors
rm bin/vncauthproxy.py
echo "running django tests..." >&2
export SYNNEFO_SETTINGS_DIR=/etc/lala
snf-manage test admin api db logic userdata --settings=synnefo.settings.test
cd ..
deactivate

#rm -rf env
#virtualenv --no-site-packages -ppython2.7 env
#source env/bin/activate
#export PIP_DOWNLOAD_CACHE=/tmp/.pip_cache
#pip install -r requirements.pip

#cd snf-common
#rm -rf build dist
#python setup.py install
#cd ../snf-cyclades-app
#rm -rf build dist
#python setup.py install
#cd ../snf-cyclades-gtools
#rm -rf build dist
#python setup.py install

#cd env
## avoid vncauthproxy errors
#rm bin/vncauthproxy.py
#echo "running django tests..." >&2
#snf-manage test aai admin api db helpdesk invitations logic userdata --settings=synnefo.settings.test
#cd ..
#deactivate
#rm -rf env
