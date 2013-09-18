# Copyright 2012 GRNET S.A. All rights reserved.
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

from pithos.api.manage_accounts import ManageAccounts
from snf_django.management.utils import pprint_table

import argparse

import os
import sys


def _double_list_str(l):
    return '\n'.join(', '.join(sublist) for sublist in l)


def list(args):
    try:
        utils = ManageAccounts()
        if args.only_duplicate:
            accounts = utils.duplicate_accounts()
        else:
            accounts = utils.existing_accounts()
        headers = ['uuid']
        table = [(a,) for a in accounts]
        if args.output_format != "json" and not args.headers:
            headers = None
        pprint_table(sys.stdout, table, headers, args.output_format)
    except Exception, e:
        sys.stderr.write('%s\n' % e)
    finally:
        utils.cleanup()


def delete(args):
    try:
        utils = ManageAccounts()
        utils.delete_account(args.delete_account, only_stats=True)

        confirm = raw_input(
            "Type 'yes' if you are sure you want "
            "to remove those entries: "
        )
        if not confirm == 'yes':
            return
        else:
            utils.delete_account(
                args.delete_account, only_stats=False, dry=args.dry
            )
    except Exception, e:
        sys.stderr.write('%s\n' % e)
    finally:
        utils.cleanup()


def merge(args):
    try:
        utils = ManageAccounts()
        utils.merge_account(
            args.src_account, args.dest_account, only_stats=True
        )

        confirm = raw_input(
            "Type 'yes' if you are sure you want"
            " to move those entries to %s: " % args.dest_account
        )
        if not confirm == 'yes':
            return
        else:
            utils.merge_account(
                args.src_account, args.dest_account, only_stats=False,
                dry=args.dry
            )
    except Exception, e:
        sys.stderr.write('%s\n' % e)
    finally:
        utils.cleanup()


def export_quota(args):
    try:
        utils = ManageAccounts()
        d = utils.backend.node.node_account_quotas()

        location = os.path.abspath(os.path.expanduser(args.location))
        f = open(location, 'w')

        for uuid, capacity in d.iteritems():
            f.write(' '.join([uuid, 'pithos.diskspace', capacity]))
            f.write('\n')
    except Exception, e:
        sys.stderr.write('%s\n' % e)
    finally:
        utils.cleanup()


def set_container_quota(args):
    try:
        utils = ManageAccounts()
        try:
            quota = int(args.quota)
        except:
            raise ValueError('Invalid quota')

        accounts = [args.account] if args.account \
            else utils.existing_accounts()

        failed = []

        def update_container_policy(account):
            trans = utils.backend.wrapper.conn.begin()
            try:
                utils.backend.update_container_policy(
                    account, account, args.container, {'quota': quota}
                )
                if args.dry:
                    print "Skipping database commit."
                    trans.rollback()
                else:
                    trans.commit()
            except Exception, e:
                failed.append((account, e))

        map(update_container_policy, accounts)
        if failed and args.report:
            sys.stdout.write(
                'Failed for the following accounts:\n'
            )
            pprint_table(sys.stdout, failed, headers=[])
    except Exception, e:
        sys.stderr.write('%s\n' % e)
    finally:
        utils.cleanup()


def main(argv=None):
    # create the top-level parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # create the parser for the "list" command
    parser_list = subparsers.add_parser(
        'list', description="List existing accounts"
    )
    parser_list.add_argument(
        '--dublicate', dest='only_duplicate', action="store_true",
        default=False, help="Display only case insensitive duplicate accounts."
    )
    parser_list.add_argument(
        "--no-headers", dest="headers", action="store_false", default=True,
        help="Do not display headers"
    )
    parser_list.add_argument(
        "--output-format", dest="output_format", metavar="[pretty, csv, json]",
        default="pretty", choices=["pretty", "csv", "json"],
        help="Select the output format: pretty [the default], tabs"
             " [tab-separated output], csv [comma-separated output]")
    parser_list.set_defaults(func=list)

    # create the parser for the "delete" command
    parser_delete = subparsers.add_parser('delete')
    parser_delete.add_argument('delete_account')
    parser_delete.add_argument(
        '--dry', action="store_true", default=False,
        help="Do not commit database changes."
    )
    parser_delete.set_defaults(func=delete)

    # create the parser for the "merge" command
    parser_merge = subparsers.add_parser('merge')
    parser_merge.add_argument('src_account')
    parser_merge.add_argument('dest_account')
    parser_merge.add_argument(
        '--dry', action="store_true", default=False,
        help="Do not commit database changes."
    )
    parser_merge.set_defaults(func=merge)

    # create the parser for the "export-quota" command
    parser_export_quota = subparsers.add_parser('export-quota')
    parser_export_quota.add_argument(
        '--location', dest='location', required=True,
        help="Where to save the exported quotas"
    )
    parser_export_quota.set_defaults(func=export_quota)

    # create the parser for the "set-container-quota" command
    parser_set_container_quota = subparsers.add_parser(
        'set-container-quota',
        description="Set container quota for all or a specific account"
    )
    parser_set_container_quota.add_argument(
        '--account', dest='account',
        help="Set container quota for a specific account"
    )
    parser_set_container_quota.add_argument(
        '--dry', action="store_true", default=False,
        help="Do not commit database changes."
    )
    parser_set_container_quota.add_argument(
        '--report', action="store_true", default=False,
        help="Report failures."
    )
    parser_set_container_quota.add_argument('container')
    parser_set_container_quota.add_argument('quota')
    parser_set_container_quota.set_defaults(func=set_container_quota)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main(sys.argv)
