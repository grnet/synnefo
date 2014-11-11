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

import OpenSSL
import sys
import base64


def cert_override(cert_contents, domain):
    """
    Generate a certificate exception entry. The result can be appended in
    `cert_override.txt`.

    https://developer.mozilla.org/en-US/docs/Cert_override.txt
    """
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                           cert_contents)

    tpl = "%(domain)s\t%(oid)s\t%(cert_hash)s" + \
          "\t%(options)s\t%(serial_hash)s\t%(issuer_hash)s"

    oid = "OID.2.16.840.1.101.3.4.2.1"
    cert_hash = cert.digest("sha256")
    options = "MU"

    serial = ("%x" % cert.get_serial_number()).decode("hex")
    issuer_parts = cert.get_issuer().der().split(".")
    issuer_name = "".join(issuer_parts[:-2])
    issuer_domain = ".".join(issuer_parts[-2:])

    serial_prefix =  "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t" + \
                     "\x00\x00\x00$\x00"
    serial_content = serial_prefix + serial + issuer_name
    serial_hash = base64.b64encode(serial_content)
    issuer_hash = base64.b64encode(issuer_domain)


    return tpl % {
        'domain': domain,
        'oid': oid,
        'cert_hash': cert_hash,
        'options': options,
        'serial_hash': serial_hash,
        'issuer_hash': issuer_hash
    }


if __name__ == "__main__":
    try:
        cert_path, domain = sys.argv[1], sys.argv[2]
    except IndexError:
        print "Usage: %s <cert_path> <domain>" % (sys.argv[0])
        exit(1)

    print cert_override(file(cert_path).read(), domain)
