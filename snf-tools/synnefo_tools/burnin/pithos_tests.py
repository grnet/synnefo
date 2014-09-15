# pylint: disable=too-many-lines

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


"""
This is the burnin class that tests the Pithos functionality

"""

import itertools
import os
import random
import tempfile
from datetime import datetime
from tempfile import NamedTemporaryFile

from synnefo_tools.burnin.common import BurninTests, Proper, \
    QPITHOS, QADD, QREMOVE, MB
from kamaki.clients import ClientError


def sample_block(fid, block):
    """Read a block from fid"""
    block_size = 4 * 1024 * 1024
    fid.seek(block * block_size)
    chars = [fid.read(1)]
    fid.seek(block_size / 2, 1)
    chars.append(fid.read(1))
    fid.seek((block + 1) * block_size - 1)
    chars.append(fid.read(1))
    return chars


# pylint: disable=too-many-public-methods
class PithosTestSuite(BurninTests):

    """Test Pithos functionality"""
    containers = Proper(value=None)
    created_container = Proper(value=None)
    now_unformated = Proper(value=datetime.utcnow())
    obj_metakey = Proper(value=None)
    large_file = Proper(value=None)
    temp_local_files = Proper(value=[])
    uvalue = u'\u03c3\u03cd\u03bd\u03bd\u03b5\u03c6\u03bf'

    def test_005_account_head(self):
        """Test account HEAD"""
        self._set_pithos_account(self._get_uuid())
        pithos = self.clients.pithos
        resp = pithos.account_head()
        self.assertEqual(resp.status_code, 204)
        self.info('Returns 204')

        resp = pithos.account_head(until='1000000000')
        self.assertEqual(resp.status_code, 204)
        datestring = unicode(resp.headers['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
        self.assertTrue(any([
            h.startswith('x-account-policy-quota') for h in resp.headers]))
        self.info('Until and account policy quota exist')

        for date_format in pithos.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(date_format)
            resp1 = pithos.account_head(
                if_modified_since=now_formated, success=(204, 304, 412))
            resp2 = pithos.account_head(
                if_unmodified_since=now_formated, success=(204, 304, 412))
            self.assertNotEqual(resp1.status_code, resp2.status_code)
        self.info('If_(un)modified_since is OK')

    # pylint: disable=too-many-locals
    def test_010_account_get(self):
        """Test account GET"""
        self.info('Preparation')
        pithos = self.clients.pithos
        for i in range(1, 3):
            cont_name = "cont%s_%s%s" % (
                i, self.run_id or 0, random.randint(1000, 9999))
            self._create_pithos_container(cont_name)
        pithos.container, obj = cont_name, 'shared_file'
        pithos.create_object(obj)
        pithos.set_object_sharing(obj, read_permission='*')
        self.info('Created object /%s/%s' % (cont_name, obj))

        #  Try to re-create the same container
        pithos.create_container(cont_name)

        resp = pithos.list_containers()
        full_len = len(resp)
        self.assertTrue(full_len >= 2)
        self.info('Normal use is OK')

        cnames = [c['name'] for c in resp]
        self.assertEqual(sorted(list(set(cnames))), sorted(cnames))
        self.info('Containers have unique names')

        resp = pithos.account_get(limit=1)
        self.assertEqual(len(resp.json), 1)
        self.info('Limit works')

        resp = pithos.account_get(marker='cont')
        cont1 = resp.json[0]
        self.info('Marker works')

        resp = pithos.account_get(limit=2, marker='cont')
        conames = [container['name'] for container in resp.json if (
            container['name'].lower().startswith('cont'))]
        self.assertTrue(cont1['name'] in conames)
        self.info('Marker-limit combination works')

        resp = pithos.account_get(show_only_shared=True)
        self.assertTrue(cont_name in [c['name'] for c in resp.json])
        self.info('Show-only-shared works')

        resp = pithos.account_get(until=1342609206.0)
        self.assertTrue(len(resp.json) <= full_len)
        self.info('Until works')

        for date_format in pithos.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(date_format)
            resp1 = pithos.account_get(
                if_modified_since=now_formated, success=(200, 304, 412))
            resp2 = pithos.account_get(
                if_unmodified_since=now_formated, success=(200, 304, 412))
            self.assertNotEqual(resp1.status_code, resp2.status_code)
        self.info('If_(un)modified_since is OK')

    def test_015_account_post(self):
        """Test account POST"""
        pithos = self.clients.pithos
        resp = pithos.account_post()
        self.assertEqual(resp.status_code, 202)
        self.info('Status code is OK')

        rand_num = '%s%s' % (self.run_id or 0, random.randint(1000, 9999))
        grp_name = 'grp%s' % rand_num
        self.assertRaises(
            ClientError, pithos.set_account_group, grp_name, [pithos.account])
        self.info('Invalid group name is handled correctly')

        rand_num = rand_num.replace('-', 'x')
        grp_name = 'grp%s' % rand_num

        uuid1, uuid2 = pithos.account, 'invalid-user-uuid-%s' % rand_num
        self.assertRaises(
            ClientError, pithos.set_account_group, grp_name, [uuid1, uuid2])
        self.info('Invalid uuid is handled correctly')

        pithos.set_account_group(grp_name, [uuid1])
        resp = pithos.get_account_group()
        self.assertEqual(resp['x-account-group-' + grp_name], '%s' % uuid1)
        self.info('Account group is OK (ascii group name)')

        grp_name_u = '%s%s' % (grp_name, self.uvalue)
        pithos.set_account_group(grp_name_u, [uuid1])
        resp = pithos.get_account_group()
        self.assertEqual(resp['x-account-group-' + grp_name_u], '%s' % uuid1)
        self.info('Account group is OK (unicode group name)')

        pithos.del_account_group(grp_name)
        resp = pithos.get_account_group()
        self.assertTrue('x-account-group-' + grp_name not in resp)
        self.info('Removed account group (ascii)')

        pithos.del_account_group(grp_name_u)
        resp = pithos.get_account_group()
        self.assertTrue('x-account-group-' + grp_name_u not in resp)
        self.info('Removed account group (unicode)')

        mprefix = 'meta%s' % rand_num
        pithos.set_account_meta({
            mprefix + '1': 'v1', mprefix + '2': 'v2'})
        resp = pithos.get_account_meta()
        self.assertEqual(resp['x-account-meta-' + mprefix + '1'], 'v1')
        self.assertEqual(resp['x-account-meta-' + mprefix + '2'], 'v2')
        self.info('Account meta is OK (ascii meta key)')

        mprefix_u, vu = '%s%s' % (mprefix, self.uvalue), 'v%s' % self.uvalue
        pithos.set_account_meta({mprefix_u: vu})
        resp = pithos.get_account_meta()
        self.assertEqual(resp['x-account-meta-' + mprefix_u], vu)
        self.info('Account meta is OK (unicode meta key)')

        pithos.del_account_meta(mprefix + '1')
        resp = pithos.get_account_meta()
        self.assertTrue('x-account-meta-' + mprefix + '1' not in resp)
        self.assertTrue('x-account-meta-' + mprefix + '2' in resp)
        self.info('Selective removal of account meta is OK (ascii)')

        pithos.del_account_meta(mprefix_u)
        resp = pithos.get_account_meta()
        self.assertTrue('x-account-meta-' + mprefix_u not in resp)
        self.info('Account meta removal is OK (unicode)')

        pithos.del_account_meta(mprefix + '2')
        self.info('Metadata cleaned up')

    def test_020_container_head(self):
        """Test container HEAD"""
        pithos = self.clients.pithos
        resp = pithos.container_head()
        self.assertEqual(resp.status_code, 204)
        self.info('Status code is OK')

        resp = pithos.container_head(until=1000000, success=(204, 404))
        self.assertEqual(resp.status_code, 404)
        self.info('Until works')

        for date_format in pithos.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(date_format)
            resp1 = pithos.container_head(
                if_modified_since=now_formated, success=(204, 304, 412))
            resp2 = pithos.container_head(
                if_unmodified_since=now_formated, success=(204, 304, 412))
            self.assertNotEqual(resp1.status_code, resp2.status_code)

        k = 'metakey%s' % random.randint(1000, 9999)
        pithos.set_container_meta({k: 'our value'})
        resp = pithos.get_container_meta()
        k = 'x-container-meta-%s' % k
        self.assertIn(k, resp)
        self.assertEqual('our value', resp[k])
        self.info('Container meta exists')

        self.obj_metakey = 'metakey%s' % random.randint(1000, 9999)
        obj = 'object_with_meta'
        pithos.create_object(obj)
        pithos.set_object_meta(obj, {self.obj_metakey: 'our value'})
        resp = pithos.get_container_object_meta()
        self.assertIn('x-container-object-meta', resp)
        self.assertIn(
            self.obj_metakey, resp['x-container-object-meta'].lower())
        self.info('Container object meta exists')

    def test_025_container_get(self):
        """Test container GET"""
        pithos = self.clients.pithos

        resp = pithos.container_get()
        self.assertEqual(resp.status_code, 200)
        self.info('Status code is OK')

        full_len = len(resp.json)
        self.assertGreater(full_len, 0)
        self.info('There are enough (%s) containers' % full_len)

        obj1 = 'test%s' % random.randint(1000, 9999)
        pithos.create_object(obj1)
        obj2 = 'test%s' % random.randint(1000, 9999)
        pithos.create_object(obj2)
        obj3 = 'another%s.test' % random.randint(1000, 9999)
        pithos.create_object(obj3)

        resp = pithos.container_get(prefix='test')
        self.assertTrue(len(resp.json) > 1)
        test_objects = [o for o in resp.json if o['name'].startswith('test')]
        self.assertEqual(len(resp.json), len(test_objects))
        self.info('Prefix is OK')

        resp = pithos.container_get(limit=1)
        self.assertEqual(len(resp.json), 1)
        self.info('Limit is OK')

        resp = pithos.container_get(marker=obj3[:-5])
        self.assertTrue(len(resp.json) > 1)
        aoobjects = [obj for obj in resp.json if obj['name'] > obj3[:-5]]
        self.assertEqual(len(resp.json), len(aoobjects))
        self.info('Marker is OK')

        resp = pithos.container_get(prefix=obj3, delimiter='.')
        self.assertTrue(full_len > len(resp.json))
        self.info('Delimiter is OK')

        resp = pithos.container_get(path='/')
        full_len += 3
        self.assertEqual(full_len, len(resp.json))
        self.info('Path is OK')

        resp = pithos.container_get(format='xml')
        self.assertEqual(resp.text.split()[4],
                         'name="' + pithos.container + '">')
        self.info('Format is OK')

        resp = pithos.container_get(meta=[self.obj_metakey, ])
        self.assertTrue(len(resp.json) > 0)
        self.info('Meta is OK')

        resp = pithos.container_get(show_only_shared=True)
        self.assertTrue(len(resp.json) < full_len)
        self.info('Show-only-shared is OK')

        try:
            resp = pithos.container_get(until=1000000000)
            datestring = unicode(resp.headers['x-account-until-timestamp'])
            self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
            self.info('Until is OK')
        except ClientError:
            pass

    def test_030_container_put(self):
        """Test container PUT"""
        pithos = self.clients.pithos
        pithos.container = 'cont%s%s' % (
            self.run_id or 0, random.randint(1000, 9999))
        self.temp_containers.append(pithos.container)

        resp = pithos.create_container()
        self.assertTrue(isinstance(resp, dict))

        resp = pithos.get_container_limit(pithos.container)
        cquota = resp.values()[0]
        newquota = 2 * int(cquota)
        self.info('Limit is OK')
        pithos.del_container()

        resp = pithos.create_container(sizelimit=newquota)
        self.assertTrue(isinstance(resp, dict))

        resp = pithos.get_container_limit(pithos.container)
        xquota = int(resp.values()[0])
        self.assertEqual(newquota, xquota)
        self.info('Can set container limit')
        pithos.del_container()

        resp = pithos.create_container(versioning='auto')
        self.assertTrue(isinstance(resp, dict))

        resp = pithos.get_container_versioning(pithos.container)
        nvers = resp.values()[0]
        self.assertEqual('auto', nvers)
        self.info('Versioning=auto is OK')
        pithos.del_container()

        resp = pithos.container_put(versioning='none')
        self.assertEqual(resp.status_code, 201)

        resp = pithos.get_container_versioning(pithos.container)
        nvers = resp.values()[0]
        self.assertEqual('none', nvers)
        self.info('Versioning=none is OK')
        pithos.del_container()

        mu, vu = 'm%s' % self.uvalue, 'v%s' % self.uvalue
        resp = pithos.create_container(metadata={'m1': 'v1', mu: vu})
        self.assertTrue(isinstance(resp, dict))

        resp = pithos.get_container_meta(pithos.container)
        self.assertTrue('x-container-meta-m1' in resp)
        self.assertEqual(resp['x-container-meta-m1'], 'v1')
        self.assertTrue('x-container-meta-' + mu in resp)
        self.assertEqual(resp['x-container-meta-' + mu], vu)

        resp = pithos.container_put(metadata={'m1': '', 'm2': 'v2a'})
        self.assertEqual(resp.status_code, 202)

        resp = pithos.get_container_meta(pithos.container)
        self.assertTrue('x-container-meta-m1' not in resp)
        self.assertTrue('x-container-meta-m2' in resp)
        self.assertEqual(resp['x-container-meta-m2'], 'v2a')
        self.info('Container meta is OK (ascii and unicode)')

        pithos.del_container_meta(pithos.container)

    # pylint: disable=too-many-statements
    def test_035_container_post(self):
        """Test container POST"""
        pithos = self.clients.pithos

        resp = pithos.container_post()
        self.assertEqual(resp.status_code, 202)
        self.info('Status is OK')

        mu, vu = 'm%s' % self.uvalue, 'v%s' % self.uvalue
        pithos.set_container_meta({'m1': 'v1', mu: vu})
        resp = pithos.get_container_meta(pithos.container)
        self.assertTrue('x-container-meta-m1' in resp)
        self.assertEqual(resp['x-container-meta-m1'], 'v1')
        self.assertTrue('x-container-meta-' + mu in resp)
        self.assertEqual(resp['x-container-meta-' + mu], vu)
        self.info('Set metadata works (ascii and unicode)')

        resp = pithos.del_container_meta('m1')
        resp = pithos.set_container_meta({mu: 'v2a'})
        resp = pithos.get_container_meta(pithos.container)
        self.assertTrue('x-container-meta-m1' not in resp)
        self.assertTrue('x-container-meta-' + mu in resp)
        self.assertEqual(resp['x-container-meta-' + mu], 'v2a')
        self.info('Modify metadata works (ascii and unicode)')

        resp = pithos.get_container_limit(pithos.container)
        cquota = resp.values()[0]
        newquota = 2 * int(cquota)
        resp = pithos.set_container_limit(newquota)
        resp = pithos.get_container_limit(pithos.container)
        xquota = int(resp.values()[0])
        self.assertEqual(newquota, xquota)
        self.info('Set quota works')

        pithos.set_container_versioning('auto')
        resp = pithos.get_container_versioning(pithos.container)
        nvers = resp.values()[0]
        self.assertEqual('auto', nvers)
        pithos.set_container_versioning('none')
        resp = pithos.get_container_versioning(pithos.container)
        nvers = resp.values()[0]
        self.assertEqual('none', nvers)
        self.info('Set versioning works')

        named_file = self._create_large_file(1024 * 1024 * 100)
        self.large_file = named_file
        self.info('Created file %s of 100 MB' % named_file.name)

        # Add file to 'temp_local_files' for cleanup
        self.temp_local_files.append(named_file.name)

        pithos.create_directory('dir')
        self.info('Upload the file ...')
        resp = pithos.upload_object('/dir/sample.file', named_file)
        for term in ('content-length', 'content-type', 'x-object-version'):
            self.assertTrue(term in resp)
        resp = pithos.get_object_info('/dir/sample.file')
        self.assertTrue(int(resp['content-length']) > 100000000)
        self.info('Made remote directory /dir and object /dir/sample.file')

        # TODO: What is tranfer_encoding? What should I check about it?

        size = os.fstat(self.large_file.fileno()).st_size
        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, size, None)]})

        obj = 'object_with_meta'
        pithos.container = self.temp_containers[-2]
        resp = pithos.object_post(
            obj, update='False', metadata={'newmeta': 'newval'})

        resp = pithos.get_object_info(obj)
        self.assertTrue('x-object-meta-newmeta' in resp)
        self.assertFalse('x-object-meta-%s' % self.obj_metakey not in resp)
        self.info('Metadata with update=False works')

    def test_040_container_delete(self):
        """Test container DELETE"""
        pithos = self.clients.pithos

        resp = pithos.container_delete(success=409)
        self.assertEqual(resp.status_code, 409)
        self.assertRaises(ClientError, pithos.container_delete)
        self.info('Successfully failed to delete non-empty container')

        resp = pithos.container_delete(until='1000000000')
        self.assertEqual(resp.status_code, 204)
        self.info('Successfully failed to delete old-timestamped container')

        obj_names = [o['name'] for o in pithos.container_get().json]
        pithos.del_container(delimiter='/')
        resp = pithos.container_get()
        self.assertEqual(len(resp.json), 0)
        self.info('Successfully emptied container')

        for obj in obj_names:
            resp = pithos.get_object_versionlist(obj)
            self.assertTrue(len(resp) > 0)
        self.info('Versions are still there')

        pithos.purge_container()
        for obj in obj_names:
            self.assertRaises(ClientError, pithos.get_object_versionlist, obj)
        self.info('Successfully purged container')

        self.temp_containers.remove(pithos.container)
        pithos.container = self.temp_containers[-1]

    def test_045_object_head(self):
        """Test object HEAD"""
        pithos = self.clients.pithos

        obj = 'dir/sample.file'
        resp = pithos.object_head(obj)
        self.assertEqual(resp.status_code, 200)
        self.info('Status code is OK')
        etag = resp.headers['etag']
        real_version = resp.headers['x-object-version']

        self.assertRaises(ClientError, pithos.object_head, obj, version=-10)
        resp = pithos.object_head(obj, version=real_version)
        self.assertEqual(resp.headers['x-object-version'], real_version)
        self.info('Version works')

        resp = pithos.object_head(obj, if_etag_match=etag)
        self.assertEqual(resp.status_code, 200)
        self.info('if-etag-match is OK')

        resp = pithos.object_head(
            obj, if_etag_not_match=etag, success=(200, 412, 304))
        self.assertNotEqual(resp.status_code, 200)
        self.info('if-etag-not-match works')

        resp = pithos.object_head(
            obj, version=real_version, if_etag_match=etag, success=200)
        self.assertEqual(resp.status_code, 200)
        self.info('Version with if-etag-match works')

        for date_format in pithos.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(date_format)
            resp1 = pithos.object_head(
                obj, if_modified_since=now_formated, success=(200, 304, 412))
            resp2 = pithos.object_head(
                obj, if_unmodified_since=now_formated, success=(200, 304, 412))
            self.assertNotEqual(resp1.status_code, resp2.status_code)
        self.info('if-(un)modified-since works')

    # pylint: disable=too-many-locals
    def test_050_object_get(self):
        """Test object GET"""
        pithos = self.clients.pithos
        obj = 'dir/sample.file'

        resp = pithos.object_get(obj)
        self.assertEqual(resp.status_code, 200)
        self.info('Status code is OK')

        osize = int(resp.headers['content-length'])
        etag = resp.headers['etag']

        resp = pithos.object_get(obj, hashmap=True)
        self.assertEqual(
            set(('hashes', 'block_size', 'block_hash', 'bytes')),
            set(resp.json))
        self.info('Hashmap works')
        hash0 = resp.json['hashes'][0]

        resp = pithos.object_get(obj, format='xml', hashmap=True)
        self.assertTrue(resp.text.split('hash>')[1].startswith(hash0))
        self.info('Hashmap with XML format works')

        rangestr = 'bytes=%s-%s' % (osize / 3, osize / 2)
        resp = pithos.object_get(obj, data_range=rangestr, success=(200, 206))
        partsize = int(resp.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1 + osize / 3)
        self.info('Range x-y works')
        orig = resp.text

        rangestr = 'bytes=%s' % (osize / 3)
        resp = pithos.object_get(
            obj, data_range=rangestr, if_range=True, success=(200, 206))
        partsize = int(resp.headers['content-length'])
        self.assertTrue(partsize, 1 + (osize / 3))
        diff = set(resp.text).symmetric_difference(set(orig[:partsize]))
        self.assertEqual(len(diff), 0)
        self.info('Range x works')

        rangestr = 'bytes=-%s' % (osize / 3)
        resp = pithos.object_get(
            obj, data_range=rangestr, if_range=True, success=(200, 206))
        partsize = int(resp.headers['content-length'])
        self.assertTrue(partsize, osize / 3)
        diff = set(resp.text).symmetric_difference(set(orig[-partsize:]))
        self.assertEqual(len(diff), 0)
        self.info('Range -x works')

        resp = pithos.object_get(obj, if_etag_match=etag)
        self.assertEqual(resp.status_code, 200)
        self.info('if-etag-match works')

        resp = pithos.object_get(obj, if_etag_not_match=etag + 'LALALA')
        self.assertEqual(resp.status_code, 200)
        self.info('if-etag-not-match works')

        for date_format in pithos.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(date_format)
            resp1 = pithos.object_get(
                obj, if_modified_since=now_formated, success=(200, 304, 412))
            resp2 = pithos.object_get(
                obj, if_unmodified_since=now_formated, success=(200, 304, 412))
            self.assertNotEqual(resp1.status_code, resp2.status_code)
        self.info('if(un)modified-since works')

        obj, dnl_f = 'dir/sample.file', NamedTemporaryFile()
        self.info('Download %s as %s ...' % (obj, dnl_f.name))
        pithos.download_object(obj, dnl_f)
        self.info('Download is completed')

        f_size = len(orig)
        for pos in (0, f_size / 2, f_size - 128):
            dnl_f.seek(pos)
            self.large_file.seek(pos)
            self.assertEqual(self.large_file.read(64), dnl_f.read(64))
        self.info('Sampling shows that files match')

        # Upload a boring file
        self.info('Create a boring file of 42 blocks...')
        bor_f = self._create_boring_file(42)
        # Add file to 'temp_local_files' for cleanup
        self.temp_local_files.append(bor_f.name)
        trg_fname = 'dir/uploaded.file'
        self.info('Now, upload the boring file as %s...' % trg_fname)
        pithos.upload_object(trg_fname, bor_f)
        self.info('Boring file %s is uploaded as %s' % (bor_f.name, trg_fname))

        size = os.fstat(bor_f.fileno()).st_size
        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, size, None)]})

        dnl_f = NamedTemporaryFile()
        # Add file to 'temp_local_files' for cleanup
        self.temp_local_files.append(dnl_f.name)
        self.info('Download boring file as %s' % dnl_f.name)
        pithos.download_object(trg_fname, dnl_f)
        self.info('File is downloaded')

        for i in range(42):
            self.assertEqual(sample_block(bor_f, i), sample_block(dnl_f, i))

    def test_053_object_put(self):
        """Test object PUT"""
        pithos = self.clients.pithos
        obj = 'sample.file'

        pithos.create_object(obj + '.FAKE')
        resp = pithos.get_object_info(obj + '.FAKE')
        self.assertEqual(
            set(resp['content-type']), set('application/octer-stream'))
        self.info('Simple call creates a new object correctly')
        ku, vu = 'key%s' % self.uvalue, 'v%s' % self.uvalue

        resp = pithos.object_put(
            obj,
            data='a',
            content_type='application/octer-stream',
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']),
            metadata={'key1': 'val1', ku: vu},
            content_encoding='UTF-8',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(resp.status_code, 201)
        self.info('Status code is OK (includes ascii and unicode metas)')
        etag = resp.headers['etag']

        resp = pithos.get_object_info(obj)
        self.assertTrue('content-disposition' in resp)
        self.assertEqual(
            resp['content-disposition'], 'attachment; filename="fname.ext"')
        self.info('Content-disposition is OK')

        sharing = resp['x-object-sharing'].split('; ')
        self.assertTrue(sharing[0].startswith('read='))
        read = set(sharing[0][5:].split(','))
        self.assertEqual(set(('u1', 'accx:groupa')), read)
        self.assertTrue(sharing[1].startswith('write='))
        write = set(sharing[1][6:].split(','))
        self.assertEqual(set(('u2', 'u3')), write)
        self.info('Permissions are OK')

        resp = pithos.get_object_meta(obj)
        self.assertEqual(resp['x-object-meta-key1'], 'val1')
        self.assertEqual(resp['x-object-meta-' + ku], vu)
        self.info('Meta are OK (ascii and unicode)')

        pithos.object_put(
            obj,
            if_etag_match=etag,
            data='b',
            content_type='application/octet-stream',
            public=True)
        self.info('If-etag-match is OK')

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 1, None)]})

        resp = pithos.object_get(obj)
        self.assertTrue('x-object-public' in resp.headers)
        self.info('Publishing works')

        etag = resp.headers['etag']
        self.assertEqual(resp.text, 'b')
        self.info('Remote object content is correct')

        resp = pithos.object_put(
            obj,
            if_etag_not_match=etag,
            data='c',
            content_type='application/octet-stream',
            success=(201, 412))
        self.assertEqual(resp.status_code, 412)
        self.info('If-etag-not-match is OK')

        resp = pithos.get_object_info('dir')
        self.assertEqual(resp['content-type'], 'application/directory')
        self.info('Directory has been created correctly')

        resp = pithos.object_put(
            '%s_v2' % obj,
            format=None,
            copy_from='/%s/%s' % (pithos.container, obj),
            content_encoding='application/octet-stream',
            source_account=pithos.account,
            content_length=0,
            success=201)
        self.assertEqual(resp.status_code, 201)
        resp1 = pithos.get_object_info(obj)
        resp2 = pithos.get_object_info('%s_v2' % obj)
        self.assertEqual(resp1['x-object-hash'], resp2['x-object-hash'])
        self.info('Object has being copied in same container, OK')

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 1, None)]})

        pithos.copy_object(
            src_container=pithos.container,
            src_object=obj,
            dst_container=self.temp_containers[-2],
            dst_object='%s_new' % obj)
        pithos.container = self.temp_containers[-2]
        resp1 = pithos.get_object_info('%s_new' % obj)
        pithos.container = self.temp_containers[-1]
        resp2 = pithos.get_object_info(obj)
        self.assertEqual(resp1['x-object-hash'], resp2['x-object-hash'])
        self.info('Object has being copied in another container, OK')

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 1, None)]})

        fromstr = '/%s/%s_new' % (self.temp_containers[-2], obj)
        resp = pithos.object_put(
            obj,
            format=None,
            copy_from=fromstr,
            content_encoding='application/octet-stream',
            source_account=pithos.account,
            content_length=0,
            success=201)
        self.assertEqual(resp.status_code, 201)
        self.info('Cross container put accepts content_encoding')

        resp = pithos.get_object_info(obj)
        self.assertEqual(resp['etag'], etag)
        self.info('Etag is OK')

        resp = pithos.object_put(
            '%s_v3' % obj,
            format=None,
            move_from=fromstr,
            content_encoding='application/octet-stream',
            source_account='nonExistendAddress@NeverLand.com',
            content_length=0,
            success=(403, ))
        self.info('Fake source account is handled correctly')

        resp1 = pithos.get_object_info(obj)
        pithos.container = self.temp_containers[-2]

        target_size_before = 0
        for o in pithos.list_objects():
            if o['name'] == obj + '_new':
                target_size_before += o['bytes']
                break

        pithos.move_object(
            src_container=self.temp_containers[-1],
            src_object=obj,
            dst_container=pithos.container,
            dst_object=obj + '_new')
        resp0 = pithos.get_object_info(obj + '_new')

        self.assertEqual(resp1['x-object-hash'], resp0['x-object-hash'])
        self.info('Cross container move is OK')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QREMOVE, target_size_before, None)]})
        pithos.container = self.temp_containers[-1]
        pithos.create_container(versioning='auto')
        pithos.upload_from_string(obj, 'first version')
        source_hashmap = pithos.get_object_hashmap(obj)['hashes']
        pithos.upload_from_string(obj, 'second version')
        pithos.upload_from_string(obj, 'third version')
        versions = pithos.get_object_versionlist(obj)
        self.assertEqual(len(versions), 3)
        vers0 = versions[0][0]

        size = len('third version')
        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, size, None)]})

        pithos.container = self.temp_containers[-2]
        pithos.object_put(
            obj,
            format=None,
            move_from='/%s/%s' % (self.temp_containers[-1], obj),
            source_version=vers0,
            content_encoding='application/octet-stream',
            content_length=0, success=201)
        target_hashmap = pithos.get_object_hashmap(obj)['hashes']
        self.info('Source-version is probably not OK (Check bug #4963)')
        source_hashmap, target_hashmap = source_hashmap, target_hashmap
        #  Comment out until it's fixed
        #  self.assertEqual(source_hashmap, target_hashmap)
        #  self.info('Source-version is OK')

        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s' % i
            pithos.object_put(
                '%s/%s' % (mobj, i),
                data='%s' % i,
                content_length=1,
                success=201,
                content_type='application/octet-stream',
                content_encoding='application/octet-stream')
        pithos.object_put(
            mobj,
            content_length=0,
            content_type='application/octet-stream',
            manifest='%s/%s' % (pithos.container, mobj))
        resp = pithos.object_get(mobj)
        self.assertEqual(resp.text, txt)
        self.info('Manifest file creation works')
        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 10, None)]})

        oldf = pithos.get_object_info('sample.file')
        named_f = self._create_large_file(1024 * 10)
        # Add file to 'temp_local_files' for cleanup
        self.temp_local_files.append(named_f.name)
        pithos.upload_object('sample.file', named_f)
        resp = pithos.get_object_info('sample.file')
        self.assertEqual(int(resp['content-length']), 10240)
        self.info('Overwrite is OK')

        size = os.fstat(named_f.fileno()).st_size - int(oldf['content-length'])
        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, size, None)]})

        # TODO: MISSING: test transfer-encoding?

    def test_054_upload_file(self):
        """Test uploading a txt file to Pithos"""
        # Create a tmp file
        with tempfile.TemporaryFile(dir=self.temp_directory) as fout:
            fout.write("This is a temp file")
            fout.seek(0, 0)
            # Upload the file,
            # The container is the one choosen during the `create_container'
            self.clients.pithos.upload_object("test.txt", fout)
            # Verify quotas
            size = os.fstat(fout.fileno()).st_size
            self._check_quotas(
                {self._get_uuid(): [(QPITHOS, QADD, size, None)]})

    def test_055_download_file(self):
        """Test downloading the file from Pithos"""
        # Create a tmp directory to save the file
        with tempfile.TemporaryFile(dir=self.temp_directory) as fout:
            self.clients.pithos.download_object("test.txt", fout)
            # Now read the file
            fout.seek(0, 0)
            contents = fout.read()
            # Compare results
            self.info("Comparing contents with the uploaded file")
            self.assertEqual(contents, "This is a temp file")

    def test_056_upload_files(self):
        """Test uploading a number of txt files to Pithos"""
        self.info('Simple call uploads %d new objects' % self.obj_upload_num)
        pithos = self.clients.pithos

        size_change = 0
        min_size = self.obj_upload_min_size
        max_size = self.obj_upload_max_size

        # Create a new container where we should upload the files
        # This will be deleted in tear-down
        self._create_pithos_container("burnin_big_files")
        self._set_pithos_container("burnin_big_files")

        hashes = {}
        open_files = []
        uuid = self._get_uuid()
        usage = self.quotas[uuid]['pithos.diskspace']['usage']
        limit = pithos.get_container_limit()
        for i, size in enumerate(random.sample(range(min_size, max_size),
                                               self.obj_upload_num)):
            assert usage + size_change + size <= limit, \
                'Not enough quotas to upload files.'
            named_file = self._create_file(size)
            # Delete temp file at tear-down
            self.temp_local_files.append(named_file.name)
            self.info('Created file %s of %s MB'
                      % (named_file.name, float(size) / MB))
            name = named_file.name.split('/')[-1]
            hashes[name] = named_file.hash
            open_files.append(dict(obj=name, f=named_file))
            size_change += size
        pithos.async_run(pithos.upload_object, open_files)
        self._check_quotas({self._get_uuid():
                            [(QPITHOS, QADD, size_change, None)]})

        r = pithos.container_get()
        self.info("Comparing hashes with the uploaded files")
        for name, hash_ in hashes.iteritems():
            try:
                o = itertools.ifilter(lambda o: o['name'] == name,
                                      r.json).next()
                assert o['x_object_hash'] == hash_, \
                    'Inconsistent hash for object: %s' % name
            except StopIteration:
                raise AssertionError('Object %s not found in the server' %
                                     name)
        self.info('Bulk upload is OK')

    def test_060_object_copy(self):
        """Test object COPY"""
        pithos = self.clients.pithos
        obj, trg = 'source.file2copy', 'copied.file'
        data = '{"key1":"val1", "key2":"val2"}'

        self._set_pithos_container(self.temp_containers[-3])

        resp = pithos.object_put(
            obj,
            content_type='application/octet-stream',
            data=data,
            metadata=dict(mkey1='mval1', mkey2='mval2'),
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']),
            content_disposition='attachment; filename="fname.ext"')
        self.info('Prepared a file /%s/%s' % (pithos.container, obj))

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        resp = pithos.object_copy(
            obj,
            destination='/%s/%s' % (pithos.container, trg),
            ignore_content_type=False, content_type='application/json',
            metadata={'mkey2': 'mval2a', },
            permissions={'write': ['u5', 'accX:groupB']})
        self.assertEqual(resp.status_code, 201)
        self.info('Status code is OK')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        resp = pithos.get_object_info(trg)
        self.assertTrue('content-disposition' in resp)
        self.info('Content-disposition is OK')

        self.assertEqual(resp['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(resp['x-object-meta-mkey2'], 'mval2a')
        self.info('Metadata are OK')

        resp = pithos.get_object_sharing(trg)
        self.assertFalse('read' in resp or 'u2' in resp['write'])
        self.assertTrue('accx:groupb' in resp['write'])
        self.info('Sharing is OK')

        resp = pithos.object_copy(
            obj,
            destination='/%s/%s' % (pithos.container, obj),
            content_encoding='utf8',
            content_type='application/json',
            destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 404))
        self.assertEqual(resp.status_code, 404)
        self.info('Non existing UUID correctly causes a 404')

        resp = pithos.object_copy(
            obj,
            destination='/%s/%s' % (self.temp_containers[-2], obj),
            content_encoding='utf8',
            content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            resp.headers['content-type'],
            'application/json; charset=UTF-8')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        # Check ignore_content_type and content_type
        pithos.container = self.temp_containers[-2]
        resp = pithos.object_get(obj)
        etag = resp.headers['etag']
        ctype = resp.headers['content-type']
        self.assertEqual(ctype, 'application/json')
        self.info('Cross container copy w. content-type/encoding is OK')

        resp = pithos.object_copy(
            obj,
            destination='/%s/%s0' % (pithos.container, obj),
            ignore_content_type=True,
            content_type='text/x-python')
        self.assertEqual(resp.status_code, 201)
        self.assertNotEqual(resp.headers['content-type'], 'application/json')
        resp = pithos.object_get(obj + '0')
        self.assertNotEqual(resp.headers['content-type'], 'text/x-python')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        resp = pithos.object_copy(
            obj,
            destination='/%s/%s1' % (pithos.container, obj),
            if_etag_match=etag)
        self.assertEqual(resp.status_code, 201)
        self.info('if-etag-match is OK')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        resp = pithos.object_copy(
            obj,
            destination='/%s/%s2' % (pithos.container, obj),
            if_etag_not_match='lalala')
        self.assertEqual(resp.status_code, 201)
        self.info('if-etag-not-match is OK')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        resp = pithos.object_copy(
            '%s2' % obj,
            destination='/%s/%s3' % (pithos.container, obj),
            format='xml',
            public=True)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue('xml' in resp.headers['content-type'])

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        resp = pithos.get_object_info(obj + '3')
        self.assertTrue('x-object-public' in resp)
        self.info('Publish, format and source-version are OK')

    def test_065_object_move(self):
        """Test object MOVE"""
        pithos = self.clients.pithos
        obj = 'source.file2move'
        data = '{"key1": "val1", "key2": "val2"}'

        resp = pithos.object_put(
            obj,
            content_type='application/octet-stream',
            data=data,
            metadata=dict(mkey1='mval1', mkey2='mval2'),
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']))
        self.info('Prepared a file /%s/%s' % (pithos.container, obj))

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QADD, len(data), None)]})

        resp = pithos.object_move(
            obj,
            destination='/%s/%s0' % (pithos.container, obj),
            ignore_content_type=False, content_type='application/json',
            metadata={'mkey2': 'mval2a'},
            permissions={'write': ['u5', 'accX:groupB']})
        self.assertEqual(resp.status_code, 201)
        self.info('Status code is OK')

        resp = pithos.get_object_meta(obj + '0')
        self.assertEqual(resp['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(resp['x-object-meta-mkey2'], 'mval2a')
        self.info('Metadata are OK')

        resp = pithos.get_object_sharing(obj + '0')
        self.assertFalse('read' in resp)
        self.assertTrue('u5' in resp['write'])
        self.assertTrue('accx:groupb' in resp['write'])
        self.info('Sharing is OK')

        self.assertRaises(ClientError, pithos.get_object_info, obj)
        self.info('Old object is not there, which is OK')

        resp = pithos.object_move(
            obj + '0',
            destination='/%s/%s' % (pithos.container, obj),
            content_encoding='utf8',
            content_type='application/json',
            destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 404))
        self.assertEqual(resp.status_code, 404)
        self.info('Non existing UUID correctly causes a 404')

        resp = pithos.object_move(
            obj + '0',
            destination='/%s/%s' % (self.temp_containers[-3], obj),
            content_encoding='utf8',
            content_type='application/json',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            resp.headers['content-type'],
            'application/json; charset=UTF-8')

        pithos.container = self.temp_containers[-3]
        resp = pithos.object_get(obj)
        etag = resp.headers['etag']
        ctype = resp.headers['content-type']
        self.assertEqual(ctype, 'application/json')
        self.assertTrue('fname.ext' in resp.headers['content-disposition'])
        self.info('Cross container copy w. content-type/encoding is OK')

        resp = pithos.object_move(
            obj,
            destination='/%s/%s0' % (pithos.container, obj),
            ignore_content_type=True,
            content_type='text/x-python')
        self.assertEqual(resp.status_code, 201)
        self.assertNotEqual(resp.headers['content-type'], 'application/json')
        resp = pithos.object_get(obj + '0')
        self.assertNotEqual(resp.headers['content-type'], 'text/x-python')

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 0, None)]})

        resp = pithos.object_move(
            obj + '0',
            destination='/%s/%s' % (pithos.container, obj),
            if_etag_match=etag)
        self.assertEqual(resp.status_code, 201)
        self.info('if-etag-match is OK')

        resp = pithos.object_move(
            obj,
            destination='/%s/%s0' % (pithos.container, obj),
            if_etag_not_match='lalala')
        self.assertEqual(resp.status_code, 201)
        self.info('if-etag-not-match is OK')

        resp = pithos.object_move(
            obj + '0',
            destination='/%s/%s' % (pithos.container, obj),
            format='xml',
            public=True)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue('xml' in resp.headers['content-type'])

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 0, None)]})

        resp = pithos.get_object_info(obj)
        self.assertTrue('x-object-public' in resp)
        self.info('Publish, format and source-version are OK')

        f_name, f_size, old_size = None, None, None
        for o in pithos.list_objects():
            if o['name'] == obj:
                old_size = o['bytes']
                break
        pithos.container = self.temp_containers[-2]
        for o in pithos.list_objects():
            if o['bytes']:
                f_name, f_size = o['name'], o['bytes']
                break
        resp = pithos.object_move(
            f_name,
            destination='/%s/%s' % (self.temp_containers[-3], obj))
        pithos.container = self.temp_containers[-3]
        for o in pithos.list_objects():
            if o['name'] == obj:
                self.assertEqual(f_size, o['bytes'])
                break
        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QREMOVE, old_size, None)]})
        self.info('Cross container MOVE is OK')

    def test_070_object_post(self):
        """Test object POST"""
        pithos = self.clients.pithos
        obj = 'sample2post.file'
        newf = NamedTemporaryFile()
        # Add file to 'temp_local_files' for cleanup
        self.temp_local_files.append(newf.name)
        newf.writelines([
            'ello!\n',
            'This is a test line\n',
            'inside a test file\n'])
        newf.flush()

        resp = pithos.object_put(
            obj,
            content_type='text/x-python',
            data='H',
            metadata=dict(mkey1='mval1', mkey2='mval2'),
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']))
        self.info(
            'Prepared a local file %s & a remote object %s', newf.name, obj)

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 1, None)]})

        newf.seek(0)
        pithos.append_object(obj, newf)
        resp = pithos.object_get(obj)
        self.assertEqual(resp.text[:5], 'Hello')
        self.info('Append is OK')

        size = os.fstat(newf.fileno()).st_size
        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, size, None)]})

        newf.seek(0)
        resp = pithos.overwrite_object(obj, 0, 10, newf)
        resp = pithos.object_get(obj)
        self.assertTrue(resp.text.startswith('ello!'))
        self.assertEqual(resp.headers['content-type'], 'text/x-python')
        self.info('Overwrite (involves content-legth/range/type) is OK')

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 0, None)]})

        resp = pithos.truncate_object(obj, 5)
        resp = pithos.object_get(obj)
        self.assertEqual(resp.text, 'ello!')
        self.assertEqual(resp.headers['content-type'], 'text/x-python')
        self.info(
            'Truncate (involves content-range, object-bytes and source-object)'
            ' is OK')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QREMOVE, size - 4, None)]})

        mu, vu = 'mk%s' % self.uvalue, 'mv%s' % self.uvalue
        pithos.set_object_meta(obj, {'mkey2': 'mval2a', mu: vu})

        resp = pithos.get_object_meta(obj)
        self.assertEqual(resp['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(resp['x-object-meta-mkey2'], 'mval2a')
        self.assertEqual(resp['x-object-meta-' + mu], vu)
        pithos.del_object_meta(obj, 'mkey1')
        resp = pithos.get_object_meta(obj)
        self.assertFalse('x-object-meta-mkey1' in resp)
        self.info('Metadata are OK (ascii and unicode)')

        pithos.set_object_sharing(
            obj, read_permission=['u4', 'u5'], write_permission=['u4'])
        resp = pithos.get_object_sharing(obj)
        self.assertTrue('read' in resp)
        self.assertTrue('u5' in resp['read'])
        self.assertTrue('write' in resp)
        self.assertTrue('u4' in resp['write'])
        pithos.del_object_sharing(obj)
        resp = pithos.get_object_sharing(obj)
        self.assertTrue(len(resp) == 0)
        self.info('Sharing is OK')

        pithos.publish_object(obj)
        resp = pithos.get_object_info(obj)
        self.assertTrue('x-object-public' in resp)
        pithos.unpublish_object(obj)
        resp = pithos.get_object_info(obj)
        self.assertFalse('x-object-public' in resp)
        self.info('Publishing is OK')

        etag = resp['etag']
        resp = pithos.object_post(
            obj,
            update=True,
            public=True,
            if_etag_not_match=etag,
            success=(412, 202, 204))
        self.assertEqual(resp.status_code, 412)
        self.info('if-etag-not-match is OK')

        resp = pithos.object_post(
            obj,
            update=True,
            public=True,
            if_etag_match=etag,
            content_type='application/octet-srteam',
            content_encoding='application/json')

        resp = pithos.get_object_info(obj)
        hello_version = resp['x-object-version']
        self.assertTrue('x-object-public' in resp)
        self.assertEqual(resp['content-type'], 'text/x-python')
        self.info('If-etag-match is OK')

        pithos.container = self.temp_containers[-2]
        pithos.create_object(obj)
        resp = pithos.object_post(
            obj,
            update=True,
            content_type='application/octet-srteam',
            content_length=5,
            content_range='bytes 1-5/*',
            source_object='/%s/%s' % (self.temp_containers[-3], obj),
            source_account='thisAccountWillNeverExist@adminland.com',
            source_version=hello_version,
            data='12345',
            success=(416, 202, 204))
        self.assertEqual(resp.status_code, 416)
        self.info('Successfully failed with invalid user UUID')

        pithos.upload_from_string(obj, '12345')
        resp = pithos.object_post(
            obj,
            update=True,
            content_type='application/octet-srteam',
            content_length=3,
            content_range='bytes 1-3/*',
            source_object='/%s/%s' % (self.temp_containers[-3], obj),
            source_account=pithos.account,
            source_version=hello_version,
            data='123',
            content_disposition='attachment; filename="fname.ext"')

        resp = pithos.object_get(obj)
        self.assertEqual(resp.text, '1ell5')
        self.info('Cross container POST with source-version/account are OK')

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 5, None)]})

        self.assertTrue('content-disposition' in resp.headers)
        self.assertTrue('fname.ext' in resp.headers['content-disposition'])
        self.info('Content-disposition POST is OK')

        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s' % i
            resp = pithos.object_put(
                '%s/%s' % (mobj, i),
                data='%s' % i,
                content_length=1,
                success=201,
                content_encoding='application/octet-stream',
                content_type='application/octet-stream')

        pithos.create_object_by_manifestation(
            mobj, content_type='application/octet-stream')

        resp = pithos.object_post(
            mobj, manifest='%s/%s' % (pithos.container, mobj))

        resp = pithos.object_get(mobj)
        self.assertEqual(resp.text, txt)
        self.info('Manifestation is OK')

        self._check_quotas({self._get_uuid(): [(QPITHOS, QADD, 10, None)]})

        # TODO: We need to check transfer_encoding

    def test_075_object_delete(self):
        """Test object DELETE"""
        pithos = self.clients.pithos
        obj = 'sample2post.file'

        resp = pithos.object_delete(obj, until=1000000)
        resp = pithos.object_get(obj, success=(200, 404))
        self.assertEqual(resp.status_code, 200)
        self.info('Successfully failed to delete with false "until"')
        size = int(resp.headers['content-length'])

        resp = pithos.object_delete(obj)
        self.assertEqual(resp.status_code, 204)
        self.info('Status code is OK')

        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QREMOVE, size, None)]})

        resp = pithos.object_get(obj, success=(200, 404))
        self.assertEqual(resp.status_code, 404)
        self.info('Successfully failed to delete a deleted file')

    def test_080_remove(self):
        """Test removing files and containers from Pithos"""
        self.created_container = self.clients.pithos.container
        fname = 'sample.file_v2'
        self.info("Removing the file %s from container %s",
                  fname, self.created_container)
        # The container is the one choosen during the `create_container'
        obj_info = self.clients.pithos.get_object_info(fname)
        content_length = obj_info['content-length']
        self.clients.pithos.del_object(fname)

        # Verify quotas
        self._check_quotas(
            {self._get_uuid(): [(QPITHOS, QREMOVE, content_length, None)]})

        self.info("Removing the container %s", self.created_container)
        self.clients.pithos.container_delete(
            self.created_container, delimiter='/')
        self.clients.pithos.purge_container()

        # List containers
        containers = self._get_list_of_containers()
        self.info("Check that the container %s has been deleted",
                  self.created_container)
        names = [n['name'] for n in containers]
        self.assertNotIn(self.created_container, names)
        # We successfully deleted our container, no need to do it
        # in our clean up phase
        self.created_container = None

    @classmethod
    def tearDownClass(cls):  # noqa
        """Clean up"""
        pithos = cls.clients.pithos
        for tcont in getattr(cls, 'temp_containers', []):
            pithos.container = tcont
            try:
                pithos.del_container(delimiter='/')
                pithos.purge_container(tcont)
            except ClientError:
                pass
        # Delete temporary files
        for tfile in getattr(cls, 'temp_local_files', []):
            try:
                os.remove(tfile)
            except OSError:
                pass
