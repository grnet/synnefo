"""
Copyright (c) 2013 Roderick Baier

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import re
import urllib
from collections import namedtuple
from posixpath import normpath


__all__ = ["ParseResult", "SplitResult", "parse", "extract", "split",
           "split_netloc", "split_host", "assemble", "encode", "normalize",
           "normalize_host", "normalize_path", "normalize_query",
           "normalize_fragment", "unquote"]


PSL_URL = 'http://mxr.mozilla.org/mozilla-central/source/netwerk/dns/effective_tld_names.dat?raw=1'

def _get_public_suffix_list():
    """Get the public suffix list.
    """
    local_psl = os.environ.get('PUBLIC_SUFFIX_LIST')
    if local_psl:
        psl_raw = open(local_psl).readlines()
    else:
        psl_raw = urllib.urlopen(PSL_URL).readlines()
    psl = set()
    for line in psl_raw:
        item = line.strip()
        if item != '' and not item.startswith('//'):
            psl.add(item)
    return psl

PSL = _get_public_suffix_list()


SCHEMES = ['http', 'https', 'ftp', 'sftp', 'file', 'gopher', 'imap', 'mms',
           'news', 'nntp', 'telnet', 'prospero', 'rsync', 'rtsp', 'rtspu',
           'svn', 'git', 'ws', 'wss']
SCHEME_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
IP_CHARS = '0123456789.:'
DEFAULT_PORT = {
    'http': '80',
    'https': '443',
    'ws': '80',
    'wss': '443',
    'ftp': '21',
    'sftp': '22'
}
UNQUOTE_EXCEPTIONS = {
    'path': ' /?+#',
    'query': ' &=+#',
    'fragment': ' +#'
}

_hextochr = {'%02x' % i: chr(i) for i in range(256)}
_hextochr.update({'%02X' % i: chr(i) for i in range(256)})
_idna_encode = lambda x: x.decode('utf-8').encode('idna')
_idna_decode = lambda x: x.decode('idna').encode('utf-8')

SplitResult = namedtuple('SplitResult', ['scheme', 'netloc', 'path', 'query',
                                         'fragment'])
ParseResult = namedtuple('ParseResult', ['scheme', 'username', 'password',
                                         'subdomain', 'domain', 'tld', 'port',
                                         'path', 'query', 'fragment'])


def normalize(url):
    """Normalize a URL
    """
    if url == '':
        return ''
    parts = split(url.strip())
    if parts.scheme:
        netloc = parts.netloc
        if parts.scheme in SCHEMES:
            path = normalize_path(parts.path)
        else:
            path = parts.path
    else:
        netloc = parts.path
        path = ''
        if '/' in netloc:
            tmp = netloc.split('/', 1)
            netloc = tmp[0]
            path = normalize_path('/' + tmp[1])
    username, password, host, port = split_netloc(netloc)
    host = normalize_host(host)
    port = normalize_port(parts.scheme, port)
    query = normalize_query(parts.query)
    fragment = normalize_fragment(parts.fragment)
    result = ParseResult(parts.scheme, username, password, None, host, None,
                         port, path, query, fragment)
    return assemble(result)


def encode(url):
    """Encode URL
    """
    parts = extract(url)
    encoded = ParseResult(*(_idna_encode(p) for p in parts))
    return assemble(encoded)


def assemble(parts):
    """Assemble a ParseResult to a new URL
    """
    nurl = ''
    if parts.scheme:
        if parts.scheme in SCHEMES:
            nurl += parts.scheme + '://'
        else:
            nurl += parts.scheme + ':'
    if parts.username and parts.password:
        nurl += parts.username + ':' + parts.password + '@'
    elif parts.username:
        nurl += parts.username + '@'
    if parts.subdomain:
        nurl += parts.subdomain + '.'
    nurl += parts.domain
    if parts.tld:
        nurl += '.' + parts.tld
    if parts.port:
        nurl += ':' + parts.port
    if parts.path:
        nurl += parts.path
    if parts.query:
        nurl += '?' + parts.query
    if parts.fragment:
        nurl += '#' + parts.fragment
    return nurl


def normalize_host(host):
    """Normalize host (decode IDNA)
    """
    if 'xn--' not in host:
        return host
    parts = host.split('.')
    return '.'.join([_idna_decode(p) for p in parts])


def normalize_port(scheme, port):
    """Check if the port is default port
    """
    if not scheme:
        return port
    if port and port != DEFAULT_PORT[scheme]:
        return port


def normalize_path(path):
    """Normalize path (collapse etc.)
    """
    if path in ['//', '/' ,'']:
        return '/'
    npath = normpath(unquote(path, exceptions=UNQUOTE_EXCEPTIONS['path']))
    if path[-1] == '/' and npath != '/':
        npath += '/'
    return npath


def normalize_query(query):
    """Normalize query (sort params by name, remove params without value)
    """
    if query == '' or len(query) <= 2:
        return ''
    nquery = unquote(query, exceptions=UNQUOTE_EXCEPTIONS['query'])
    params = nquery.split('&')
    nparams = []
    for param in params:
        if '=' in param:
            k, v = param.split('=', 1)
            if k and v:
                nparams.append("%s=%s" % (k, v))
    nparams.sort()
    return '&'.join(nparams)


def normalize_fragment(fragment):
    """Normalize fragment (unquote with exceptions only)
    """
    return unquote(fragment, UNQUOTE_EXCEPTIONS['fragment'])


def unquote(text, exceptions=[]):
    """Unquote a text but ignore the exceptions
    """
    if '%' not in text:
        return text
    s = text.split('%')
    res = [s[0]]
    for h in s[1:]:
        c = _hextochr.get(h[:2])
        if c and c not in exceptions:
            if len(h) > 2:
                res.append(c + h[2:])
            else:
                res.append(c)
        else:
            res.append('%' + h)
    return ''.join(res)


def parse(url):
    """Parse a URL
    """
    parts = split(url)
    if parts.scheme:
        (username, password, host, port) = split_netloc(parts.netloc)
        (subdomain, domain, tld) = split_host(host)
    else:
        username = password = subdomain = domain = tld = port = ''
    return ParseResult(parts.scheme, username, password, subdomain, domain, tld,
                       port, parts.path, parts.query, parts.fragment)


def extract(url):
    """Extract as much information from a (relative) URL as possible
    """
    parts = split(url)
    if parts.scheme:
        netloc = parts.netloc
        path = parts.path
    else:
        netloc = parts.path
        path = ''
        if '/' in netloc:
            tmp = netloc.split('/', 1)
            netloc = tmp[0]
            path = '/' + tmp[1]
    (username, password, host, port) = split_netloc(netloc)
    (subdomain, domain, tld) = split_host(host)
    return ParseResult(parts.scheme, username, password, subdomain, domain, tld,
                       port, path, parts.query, parts.fragment)


def split(url):
    """Split URL into scheme, netloc, path, query and fragment
    """
    scheme = netloc = path = query = fragment = ''
    ip6_start = url.find('[')
    scheme_end = url.find(':')
    if ip6_start > 0 and ip6_start < scheme_end:
        scheme_end = -1
    if scheme_end > 0:
        for c in url[:scheme_end]:
            if c not in SCHEME_CHARS:
                break
        else:
            scheme = url[:scheme_end].lower()
            rest = url[scheme_end:].lstrip(':/')
    if not scheme:
        rest = url
    l_path = rest.find('/')
    l_query = rest.find('?')
    l_frag = rest.find('#')
    if l_path > 0:
        if l_query > 0 and l_frag > 0:
            netloc = rest[:l_path]
            path = rest[l_path:min(l_query, l_frag)]
        elif l_query > 0:
            if l_query > l_path:
                netloc = rest[:l_path]
                path = rest[l_path:l_query]
            else:
                netloc = rest[:l_query]
                path = ''
        elif l_frag > 0:
            netloc = rest[:l_path]
            path = rest[l_path:l_frag]
        else:
            netloc = rest[:l_path]
            path = rest[l_path:]
    else:
        if l_query > 0:
            netloc = rest[:l_query]
        elif l_frag > 0:
            netloc = rest[:l_frag]
        else:
            netloc = rest
    if l_query > 0:
        if l_frag > 0:
            query = rest[l_query+1:l_frag]
        else:
            query = rest[l_query+1:]
    if l_frag > 0:
        fragment = rest[l_frag+1:]
    if not scheme:
        path = netloc + path
        netloc = ''
    return SplitResult(scheme, netloc, path, query, fragment)


def _clean_netloc(netloc):
    """Remove trailing '.' and ':' and tolower
    """
    try:
        netloc.encode('ascii')
    except:
        return netloc.rstrip('.:').decode('utf-8').lower().encode('utf-8')
    else:
        return netloc.rstrip('.:').lower()


def split_netloc(netloc):
    """Split netloc into username, password, host and port
    """
    username = password = host = port = ''
    if '@' in netloc:
        user_pw, netloc = netloc.split('@', 1)
        if ':' in user_pw:
            username, password = user_pw.split(':', 1)
        else:
            username = user_pw
    netloc = _clean_netloc(netloc)
    if ':' in netloc and netloc[-1] != ']':
        host, port = netloc.rsplit(':', 1)
    else:
        host = netloc
    return username, password, host, port


def split_host(host):
    """Use the Public Suffix List to split host into subdomain, domain and tld
    """
    if '[' in host:
        return '', host, ''
    domain = subdomain = tld = ''
    for c in host:
        if c not in IP_CHARS:
            break
    else:
        return '', host, ''
    parts = host.split('.')
    for i in range(len(parts)):
        tld = '.'.join(parts[i:])
        wildcard_tld = '*.' + tld
        exception_tld = '!' + tld
        if exception_tld in PSL:
            domain = '.'.join(parts[:i+1])
            tld = '.'.join(parts[i+1:])
            break
        if tld in PSL:
            domain = '.'.join(parts[:i])
            break
        if wildcard_tld in PSL:
            domain = '.'.join(parts[:i-1])
            tld = '.'.join(parts[i-1:])
            break
    if '.' in domain:
        (subdomain, domain) = domain.rsplit('.', 1) 
    return subdomain, domain, tld
