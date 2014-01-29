# Copyright (C) 2010, 2011, 2012, 2013 GRNET S.A. All rights reserved.
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
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A. OR
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

import datetime
from snfdeploy.utils import debug


class SynnefoComponent(object):

    REQUIRED_PACKAGES = []

    def debug(self, msg, info=""):
        debug(self.__class__.__name__, msg, info)

    def __init__(self, node_info, env, *args, **kwargs):
        """ Take a node_info and env as argument and initialize local vars """
        self.node_info = node_info
        self.env = env

    def check(self):
        """ Returns a list of bash commands that check prerequisites """
        return []

    def install(self):
        """ Returns a list of debian packages to install """
        return self.REQUIRED_PACKAGES

    def prepare(self):
        """ Returs a list of bash commands that prepares the component """
        return []

    def configure(self):
        """ Must return a list of tuples (tmpl_path, replace_dict, mode) """
        return []

    def initialize(self):
        """ Returs a list of bash commands that initialize the component """
        return []

    def test(self):
        """ Returs a list of bash commands that test existing installation """
        return []

    def restart(self):
        return []

    #TODO: add cleanup method for each component
    def clean(self):
        return []


class HW(SynnefoComponent):
    def test(self):
        return [
            "ping -c 1 %s" % self.node_info.ip,
            "ping -c 1 www.google.com",
            "apt-get update",
            ]


class SSH(SynnefoComponent):
    def prepare(self):
        return [
            "mkdir -p /root/.ssh",
            "for f in $(ls /root/.ssh/*); do cp $f $f.bak ; done",
            "echo StrictHostKeyChecking no >> /etc/ssh/ssh_config",
            ]

    def configure(self):
        files = [
            "authorized_keys", "id_dsa", "id_dsa.pub", "id_rsa", "id_rsa.pub"
            ]
        ssh = [("/root/.ssh/%s" % f, {}, {"mode": 0600}) for f in files]
        return ssh

    def initialize(self):
        f = "/root/.ssh/authorized_keys"
        return [
            "test -e {0}.bak && cat {0}.bak >> {0}".format(f)
            ]

    def test(self):
        return ["ssh %s date" % self.node_info.ip]


class DNS(SynnefoComponent):
    def prepare(self):
        return [
            "chattr -i /etc/resolv.conf",
            "sed -i 's/^127.*$/127.0.0.1 localhost/g' /etc/hosts",
            ]

    def configure(self):
        r1 = {
            "date": str(datetime.datetime.today()),
            "domain": self.env.env.domain,
            "ns_node_ip": self.env.env.ns.ip,
            }
        resolv = [
            ("/etc/resolv.conf", r1, {})
            ]
        return resolv

    def initialize(self):
        return ["chattr +i /etc/resolv.conf"]


class DDNS(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "dnsutils",
        ]

    def prepare(self):
        return [
            "mkdir -p /root/ddns/"
            ]

    def configure(self):
        return [
            ("/root/ddns/" + k, {}, {}) for k in self.env.env.ddns_keys
            ]


class NS(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "bind9",
        ]

    def nsupdate(self, cmd):
        ret = """
nsupdate -k {0} > /dev/null <<EOF || true
server {1}
{2}
send
EOF
""".format(self.env.env.ddns_private_key, self.node_info.ip, cmd)
        return ret

    def prepare(self):
        return [
            "mkdir -p /etc/bind/zones",
            "chmod g+w /etc/bind/zones",
            "mkdir -p /etc/bind/rev",
            "chmod g+w /etc/bind/rev",
            ]

    def configure(self):
        d = self.env.env.domain
        ip = self.node_info.ip
        return [
            ("/etc/bind/named.conf.local", {"domain": d}, {}),
            ("/etc/bind/zones/example.com",
             {"domain": d, "ns_node_ip": ip},
             {"remote": "/etc/bind/zones/%s" % d}),
            ("/etc/bind/zones/vm.example.com",
             {"domain": d, "ns_node_ip": ip},
             {"remote": "/etc/bind/zones/vm.%s" % d}),
            ("/etc/bind/rev/synnefo.in-addr.arpa.zone", {"domain": d}, {}),
            ("/etc/bind/rev/synnefo.ip6.arpa.zone", {"domain": d}, {}),
            ("/etc/bind/named.conf.options",
             {"node_ips": ";".join(self.env.env.ips)}, {}),
            ("/root/ddns/ddns.key", {}, {"remote": "/etc/bind/ddns.key"}),
            ]

    def update_cnamerecord(self, node_info):
        return self.nsupdate("update add %s" % node_info.cnamerecord)

    def update_arecord(self, node_info):
        return self.nsupdate("update add %s" % node_info.arecord)

    def update_ptrrecord(self, node_info):
        return self.nsupdate("update add %s" % node_info.ptrrecord)

    def update_ns_for_node(self, node_info):
        return [
            self.update_arecord(node_info),
            self.update_cnamerecord(node_info),
            self.update_ptrrecord(node_info)
            ]

    def initialize(self):
        a = [self.update_arecord(n)
             for n in self.env.env.nodes_info.values()]
        ptr = [self.update_ptrrecord(n)
               for n in self.env.env.nodes_info.values()]
        cnames = [self.update_cnamerecord(n)
                  for n in self.env.env.roles_info.values()]

        return a + ptr + cnames

    def restart(self):
        return ["/etc/init.d/bind9 restart"]

    def test(self):
        n = ["host %s localhost" % i.fqdn
             for i in self.env.env.nodes_info.values()]
        a = ["host %s localhost" % i.fqdn
             for i in self.env.env.roles_info.values()]
        return n + a


class APT(SynnefoComponent):
    """ Setup apt repos and check fqdns """
    REQUIRED_PACKAGES = ["curl"]

    def prepare(self):
        return [
            "echo 'APT::Install-Suggests \"false\";' >> /etc/apt/apt.conf",
            "curl -k https://dev.grnet.gr/files/apt-grnetdev.pub | \
                apt-key add -",
            ]

    def configure(self):
        return [
            ("/etc/apt/sources.list.d/synnefo.wheezy.list", {}, {})
            ]

    def initialize(self):
        return [
            "apt-get update",
            ]


class MQ(SynnefoComponent):
    REQUIRED_PACKAGES = ["rabbitmq-server"]

    def check(self):
        return ["ping -c 1 mq.%s" % self.env.env.domain]

    def initialize(self):
        u = self.env.env.synnefo_user
        p = self.env.env.synnefo_rabbitmq_passwd
        return [
            "rabbitmqctl add_user %s %s" % (u, p),
            "rabbitmqctl set_permissions %s \".*\" \".*\" \".*\"" % u,
            "rabbitmqctl delete_user guest",
            "rabbitmqctl set_user_tags %s administrator" % u,
            ]


class DB(SynnefoComponent):
    REQUIRED_PACKAGES = ["postgresql"]

    def check(self):
        return ["ping -c 1 db.%s" % self.env.env.domain]

    def get_user_info_from_db(self):
        cmd = """
cat > /tmp/psqlcmd <<EOF
select id, auth_token, uuid, email from auth_user, im_astakosuser \
where auth_user.id = im_astakosuser.user_ptr_id and auth_user.email = '{0}';
EOF

su - postgres -c  "psql -w -d snf_apps -f /tmp/psqlcmd"
""".format(self.env.env.user_email)

        return [cmd]

    def allow_access_in_db(self, node_info, user="all", method="md5"):
        f = "/etc/postgresql/*/main/pg_hba.conf"
        cmd1 = "echo host all %s %s/32 %s >> %s" % \
            (user, node_info.ip, method, f)
        cmd2 = "sed -i 's/\(host.*127.0.0.1.*\)md5/\\1trust/' %s" % f
        return [cmd1, cmd2] + self.restart()

    def configure(self):
        u = self.env.env.synnefo_user
        p = self.env.env.synnefo_db_passwd
        replace = {"synnefo_user": u, "synnefo_db_passwd": p}
        return [
            ("/tmp/db-init.psql", replace, {}),
            ]

    def make_db_fast(self):
        f = "/etc/postgresql/*/main/postgresql.conf"
        opts = "fsync=off\nsynchronous_commit=off\nfull_page_writes=off\n"
        return ["""echo -e "%s" >> %s""" % (opts, f)]

    def prepare(self):
        f = "/etc/postgresql/*/main/postgresql.conf"
        return [
            """echo "listen_addresses = '*'" >> %s""" % f,
            ]

    def initialize(self):
        script = "/tmp/db-init.psql"
        cmd = "su - postgres -c \"psql -w -f %s\" " % script
        return [cmd]

    def restart(self):
        return ["/etc/init.d/postgresql restart"]

    def destroy_db(self):
        return [
            """su - postgres -c ' psql -w -c "drop database snf_apps" '""",
            """su - postgres -c ' psql -w -c "drop database snf_pithos" '"""
            ]


class Ganeti(SynnefoComponent):

    REQUIRED_PACKAGES = [
        "qemu-kvm",
        "python-bitarray",
        "ganeti-htools",
        "ganeti-haskell",
        "snf-ganeti",
        "ganeti2",
        "bridge-utils",
        "lvm2",
        "drbd8-utils",
        ]

    def check(self):
        commands = [
            "getent hosts %s | grep -v ^127" % self.node_info.hostname,
            "hostname -f | grep %s" % self.node_info.fqdn,
            ]
        return commands

    def configure(self):
        return [
            ("/etc/ganeti/file-storage-paths", {}, {}),
            ]

    def prepare_lvm(self):
        return [
            "pvcreate %s" % self.env.env.extra_disk,
            "vgcreate %s %s" % (self.env.env.extra_disk, self.env.env.vg)
            ]

    def prepare_net_infra(self):
        br = self.env.env.common_bridge
        return [
            "brctl addbr {0}; ip link set {0} up".format(br)
            ]

    def prepare(self):
        return [
            "mkdir -p /srv/ganeti/file-storage/",
            "sed -i 's/^127.*$/127.0.0.1 localhost/g' /etc/hosts"
            ] + self.prepare_net_infra()

    def restart(self):
        return ["/etc/init.d/ganeti restart"]


class Master(SynnefoComponent):
    def add_rapi_user(self):
        user = self.env.env.synnefo_user
        passwd = self.env.env.synnefo_rapi_passwd
        x = "%s:Ganeti Remote API:%s" % (user, passwd)

        cmd = """
cat >> /var/lib/ganeti/rapi/users <<EOF
%s {HA1}$(echo -n %s | openssl md5 | sed 's/^.* //') write
EOF
""" % (self.env.env.synnefo_user, x)

        return [cmd] + self.restart()

    def add_node(self, node_info):
        commands = [
            "gnt-node add --no-ssh-key-check --master-capable=yes " +
            "--vm-capable=yes " + node_info.fqdn,
            ]
        return commands

    def try_use_vg(self):
        vg = self.env.env.vg
        return [
            "gnt-cluster modify --vg-name=%s || true" % vg,
            "gnt-cluster modify --disk-parameters=drbd:metavg=%s" % vg,
            "gnt-group modify --disk-parameters=drbd:metavg=%s default" % vg,
            ]

    def initialize(self):
        cmd = """
        gnt-cluster init --enabled-hypervisors=kvm \
            --no-lvm-storage --no-drbd-storage \
            --nic-parameters link={0},mode=bridged \
            --master-netdev {1} \
            --specs-nic-count min=0,max=8 \
            --default-iallocator hail \
            --hypervisor-parameters kvm:kernel_path=,vnc_bind_address=0.0.0.0 \
            --no-ssh-init --no-etc-hosts \
            --enabled-disk-templates file,plain,ext,drbd \
            {2}
        """.format(self.env.env.common_bridge,
                   self.env.env.cluster_netdev, self.env.env.cluster.fqdn)

        return [cmd] + self.try_use_vg() + self.add_rapi_user()

    def restart(self):
        return ["/etc/init.d/ganeti restart"]


class Image(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "snf-pithos-backend",
        "snf-image",
        ]

    def check(self):
        return ["mkdir -p %s" % self.env.env.image_dir]

    def configure(self):
        tmpl = "/etc/default/snf-image"
        replace = {
            "synnefo_user": self.env.env.synnefo_user,
            "synnefo_db_passwd": self.env.env.synnefo_db_passwd,
            "pithos_dir": self.env.env.pithos_dir,
            "db_node": self.env.env.db.ip,
            "image_dir": self.env.env.image_dir,
            }
        return [(tmpl, replace, {})]

    def initialize(self):
        return ["snf-image-update-helper -y"]


class GTools(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "snf-cyclades-gtools",
        ]

    def check(self):
        return ["ping -c1 %s" % self.env.env.mq.ip]

    def configure(self):
        tmpl = "/etc/synnefo/gtools.conf"
        replace = {
            "synnefo_user": self.env.env.synnefo_user,
            "synnefo_rabbitmq_passwd": self.env.env.synnefo_rabbitmq_passwd,
            "mq_node": self.env.env.mq.ip,
            }
        return [(tmpl, replace, {})]

    def initialize(self):
        return [
            "sed -i 's/false/true/' /etc/default/snf-ganeti-eventd",
            "/etc/init.d/snf-ganeti-eventd start",
            ]

    def restart(self):
        return ["/etc/init.d/snf-ganeti-eventd restart"]


class Network(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "python-nfqueue",
        "snf-network",
        "nfdhcpd",
        ]

    def configure(self):
        r1 = {
            "ns_node_ip": self.env.env.ns.ip
            }
        r2 = {
            "common_bridge": self.env.env.common_bridge,
            "public_iface": self.env.env.public_iface,
            "subnet": self.env.env.synnefo_public_network_subnet,
            "gateway": self.env.env.synnefo_public_network_gateway,
            "router_ip": self.env.env.router.ip,
            "node_ip": self.node_info.ip,
            }
        r3 = {
            "domain": self.env.env.domain,
            "server": self.env.env.ns.ip,
            "keyfile": self.env.env.ddns_private_key,
            }

        return [
            ("/etc/nfdhcpd/nfdhcpd.conf", r1, {}),
            ("/etc/rc.local", r2, {"mode": 0755}),
            ("/etc/default/snf-network", r3, {}),
            ]

    def initialize(self):
        return ["/etc/init.d/rc.local start"]

    def restart(self):
        return ["/etc/init.d/nfdhcpd restart"]


class Apache(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "apache2",
        ]

    def prepare(self):
        return [
            "a2enmod ssl", "a2enmod rewrite", "a2dissite default",
            "a2enmod headers",
            "a2enmod proxy_http", "a2dismod autoindex",
            ]

    def configure(self):
        r1 = {"HOST": self.node_info.fqdn}
        return [
            ("/etc/apache2/sites-available/synnefo", r1, {}),
            ("/etc/apache2/sites-available/synnefo-ssl", r1, {}),
            ]

    def initialize(self):
        return [
            "a2ensite synnefo", "a2ensite synnefo-ssl",
            ]

    def restart(self):
        return [
            "/etc/init.d/apache2 restart",
            ]


class Gunicorn(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "gunicorn",
        ]

    def prepare(self):
        return [
            "chown root.www-data /var/log/gunicorn",
            ]

    def configure(self):
        r1 = {"HOST": self.node_info.fqdn}
        return [
            ("/etc/gunicorn.d/synnefo", r1, {}),
            ]

    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]


class Common(SynnefoComponent):
    REQUIRED_PACKAGES = [
        # snf-common
        "python-objpool",
        "snf-common",
        "python-astakosclient",
        "snf-django-lib",
        "snf-branding",
        ]

    def configure(self):
        r1 = {
            "EMAIL_SUBJECT_PREFIX": self.node_info.hostname,
            "domain": self.env.env.domain,
            "HOST": self.node_info.fqdn,
            "MAIL_DIR": self.env.env.mail_dir,
            }
        return [
            ("/etc/synnefo/common.conf", r1, {}),
            ]

    def initialize(self):
        return ["mkdir -p {0}; chmod 777 {0}".format(self.env.env.mail_dir)]

    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]


class WEB(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "snf-webproject",
        "python-psycopg2",
        "python-gevent",
        "python-django",
        ]

    def check(self):
        return ["ping -c1 %s" % self.env.env.db.fqdn]

    def configure(self):
        r1 = {
            "synnefo_user": self.env.env.synnefo_user,
            "synnefo_db_passwd": self.env.env.synnefo_db_passwd,
            "db_node": self.env.env.db.fqdn,
            "domain": self.env.env.domain,
            }
        return [
            ("/etc/synnefo/webproject.conf", r1, {}),
            ]

    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]


class Astakos(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "python-django-south",
        "snf-astakos-app",
        "kamaki",
        ]

    def export_service(self):
        f = self.env.jsonfile
        return [
            "snf-manage service-export-astakos > %s" % f
            ]

    def import_service(self):
        f = self.env.jsonfile
        return [
            "snf-manage service-import --json=%s" % f
            ]

    def set_default_quota(self):
        cmd = "snf-manage resource-modify --default-quota"
        return [
            "%s 40G pithos.diskspace" % cmd,
            "%s 2 astakos.pending_app" % cmd,
            "%s 4 cyclades.vm" % cmd,
            "%s 40G cyclades.disk" % cmd,
            "%s 16G cyclades.total_ram" % cmd,
            "%s 8G cyclades.ram" % cmd,
            "%s 32 cyclades.total_cpu" % cmd,
            "%s 16 cyclades.cpu" % cmd,
            "%s 4 cyclades.network.private" % cmd,
            "%s 4 cyclades.floating_ip" % cmd,
            ]

    def modify_all_quota(self):
        cmd = "snf-manage user-modify -f --all --base-quota"
        return [
            "%s pithos.diskspace 40G" % cmd,
            "%s astakos.pending_app 2" % cmd,
            "%s cyclades.vm 4" % cmd,
            "%s cyclades.disk 40G" % cmd,
            "%s cyclades.total_ram 16G" % cmd,
            "%s cyclades.ram 8G" % cmd,
            "%s cyclades.total_cpu 32" % cmd,
            "%s cyclades.cpu 16" % cmd,
            "%s cyclades.network.private 4" % cmd,
            "%s cyclades.floating_ip 4" % cmd,
            ]

    def get_services(self):
        return [
            "snf-manage component-list -o id,name,token"
            ]

    def configure(self):
        r1 = {
            "ACCOUNTS": self.env.env.accounts.fqdn,
            "domain": self.env.env.domain,
            "CYCLADES": self.env.env.cyclades.fqdn,
            "PITHOS": self.env.env.pithos.fqdn,
            }
        return [
            ("/etc/synnefo/astakos.conf", r1, {})
            ]

    def initialize(self):
        secret = self.env.env.oa2_secret
        view = "https://%s/pithos/ui/view" % self.env.env.pithos.fqdn
        oa2 = "snf-manage oauth2-client-add pithos-view \
                  --secret=%s --is-trusted --url %s" % (secret, view)

        return [
            "snf-manage syncdb --noinput",
            "snf-manage migrate im --delete-ghost-migrations",
            "snf-manage migrate quotaholder_app",
            "snf-manage migrate oa2",
            "snf-manage loaddata groups",
            oa2
            ] + self.astakos_register_components()

    def astakos_register_components(self):
        # base urls
        cbu = "https://%s/cyclades" % self.env.env.cyclades.fqdn
        pbu = "https://%s/pithos" % self.env.env.pithos.fqdn
        abu = "https://%s/astakos" % self.env.env.accounts.fqdn
        cmsurl = "https://%s/home" % self.env.env.cms.fqdn

        cmd = "snf-manage component-add"
        h = "%s home --base-url %s --ui-url %s" % (cmd, cmsurl, cmsurl)
        c = "%s cyclades --base-url %s --ui-url %s/ui" % (cmd, cbu, cbu)
        p = "%s pithos --base-url %s --ui-url %s/ui" % (cmd, pbu, pbu)
        a = "%s astakos --base-url %s --ui-url %s/ui" % (cmd, abu, abu)

        return [h, c, p, a]

    def add_user(self):
        info = (
            self.env.env.user_passwd,
            self.env.env.user_email,
            self.env.env.user_name,
            self.env.env.user_lastname,
            )
        cmd = "snf-manage user-add --password %s %s %s %s" % info
        return [cmd]

    def activate_user(self):
        user_id = self.env.user_id
        return [
            "snf-manage user-modify --verify %s" % user_id,
            "snf-manage user-modify --accept %s" % user_id,
            ]


class CMS(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "snf-cloudcms"
        ]

    def configure(self):
        r1 = {
            "ACCOUNTS": self.env.env.accounts.fqdn
            }
        r2 = {
            "DOMAIN": self.env.env.domain
            }
        return [
            ("/etc/synnefo/cms.conf", r1, {}),
            ("/tmp/sites.json", r2, {}),
            ("/tmp/page.json", {}, {}),
            ]

    def initialize(self):
        return [
            "snf-manage syncdb",
            "snf-manage migrate --delete-ghost-migrations",
            "snf-manage loaddata /tmp/sites.json",
            "snf-manage loaddata /tmp/page.json",
            "snf-manage createsuperuser --username=admin \
                  --email=admin@%s --noinput" % self.env.env.domain,
            ]

    def restart(self):
        return ["/etc/init.d/gunicorn restart"]


class Mount(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "nfs-common"
        ]

    def prepare(self):
        ret = []
        for d in [self.env.env.pithos_dir, self.env.env.image_dir]:
            ret.append("mkdir -p %s" % d)
            cmd = """
cat >> /etc/fstab <<EOF
{0}:{1} {1}  nfs defaults,rw,noatime,rsize=131072,wsize=131072 0 0
EOF
""".format(self.env.env.pithos.ip, d)
            ret.append(cmd)

        return ret

    def initialize(self):
        ret = []
        for d in [self.env.env.pithos_dir, self.env.env.image_dir]:
            ret.append("mount %s" % d)
        return ret


class NFS(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "nfs-kernel-server"
        ]

    def prepare_image(self):
        url = self.env.env.debian_base_url
        d = self.env.env.image_dir
        image = "debian_base.diskdump"
        return ["wget %s -O %s/%s" % (url, d, image)]

    def prepare(self):
        p = self.env.env.pithos_dir
        return [
            "mkdir -p %s" % self.env.env.image_dir,
            "mkdir -p %s/data" % p,
            "chown www-data.www-data %s/data" % p,
            "chmod g+ws %s/data" % p,
            ] + self.prepare_image()

    def update_exports(self, node_info):
        cmd = """
cat >> /etc/exports <<EOF
{0} {2}(rw,async,no_subtree_check,no_root_squash)
{1} {2}(rw,async,no_subtree_check,no_root_squash)
EOF
""".format(self.env.env.pithos_dir, self.env.env.image_dir, node_info.ip)
        return [cmd] + self.restart()

    def restart(self):
        return ["exportfs -a"]


class Pithos(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "kamaki",
        "snf-pithos-backend",
        "snf-pithos-app",
        "snf-pithos-webclient",
        ]

    def export_service(self):
        f = self.env.jsonfile
        return [
            "snf-manage service-export-pithos > %s" % f
            ]

    def configure(self):
        r1 = {
            "ACCOUNTS": self.env.env.accounts.fqdn,
            "PITHOS": self.env.env.pithos.fqdn,
            "db_node": self.env.env.db.ip,
            "synnefo_user": self.env.env.synnefo_user,
            "synnefo_db_passwd": self.env.env.synnefo_db_passwd,
            "pithos_dir": self.env.env.pithos_dir,
            "PITHOS_SERVICE_TOKEN": self.env.service_token,
            "oa2_secret": self.env.env.oa2_secret,
            }
        r2 = {
            "ACCOUNTS": self.env.env.accounts.fqdn,
            "PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE": self.env.service_id,
            }

        return [
            ("/etc/synnefo/pithos.conf", r1, {}),
            ("/etc/synnefo/webclient.conf", r2, {}),
            ]

    def initialize(self):
        return ["pithos-migrate stamp head"]


class Cyclades(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "memcached",
        "python-memcache",
        "snf-pithos-backend",
        "kamaki",
        "snf-cyclades-app",
        "python-django-south",
        ]

    def add_network(self):
        subnet = self.env.env.synnefo_public_network_subnet
        gw = self.env.env.synnefo_public_network_gateway
        ntype = self.env.env.synnefo_public_network_type
        link = self.env.env.common_bridge

        cmd = """
snf-manage network-create --subnet={0} --gateway={1} --public \
  --dhcp=True --flavor={2} --mode=bridged --link={3} --name=Internet \
  --floating-ip-pool=True
""".format(subnet, gw, ntype, link)

        return [cmd]

    def add_network6(self):
        subnet = "babe::/64"
        gw = "babe::1"
        ntype = self.env.env.synnefo_public_network_type
        link = self.env.env.common_bridge

        cmd = """
snf-manage network-create --subnet6={0} \
      --gateway6={1} --public --dhcp=True --flavor={2} --mode=bridged \
       --link={3} --name=IPv6PublicNetwork
""".format(subnet, gw, ntype, link)

        return [cmd]

    def export_service(self):
        f = self.env.jsonfile
        return [
            "snf-manage service-export-cyclades > %s" % f
            ]

    def list_backends(self):
        return [
            "snf-manage backend-list"
            ]

    def add_backend(self):
        cluster = self.env.env.cluster
        user = self.env.env.synnefo_user
        passwd = self.env.env.synnefo_rapi_passwd
        return [
            "snf-manage backend-add --clustername=%s --user=%s --pass=%s" %
            (cluster.fqdn, user, passwd)
            ]

    def undrain_backend(self):
        backend_id = self.env.backend_id
        return [
            "snf-manage backend-modify --drained=False %s" % str(backend_id)
            ]

    def prepare(self):
        return ["sed -i 's/false/true/' /etc/default/snf-dispatcher"]

    def configure(self):
        r1 = {
            "ACCOUNTS": self.env.env.accounts.fqdn,
            "CYCLADES": self.env.env.cyclades.fqdn,
            "mq_node": self.env.env.mq.ip,
            "db_node": self.env.env.db.ip,
            "synnefo_user": self.env.env.synnefo_user,
            "synnefo_db_passwd": self.env.env.synnefo_db_passwd,
            "synnefo_rabbitmq_passwd": self.env.env.synnefo_rabbitmq_passwd,
            "pithos_dir": self.env.env.pithos_dir,
            "common_bridge": self.env.env.common_bridge,
            "HOST": self.env.env.cyclades.ip,
            "domain": self.env.env.domain,
            "CYCLADES_SERVICE_TOKEN": self.env.service_token,
            "STATS": self.env.env.stats.fqdn,
            "SYNNEFO_VNC_PASSWD": self.env.env.synnefo_vnc_passwd,
            "CYCLADES_NODE_IP": self.env.env.cyclades.ip
            }
        return [
            ("/etc/synnefo/cyclades.conf", r1, {})
            ]

    def initialize(self):
        cpu = self.env.env.flavor_cpu
        ram = self.env.env.flavor_ram
        disk = self.env.env.flavor_disk
        storage = self.env.env.flavor_storage
        return [
            "snf-manage syncdb",
            "snf-manage migrate --delete-ghost-migrations",
            "snf-manage pool-create --type=mac-prefix \
              --base=aa:00:0 --size=65536",
            "snf-manage pool-create --type=bridge --base=prv --size=20",
            "snf-manage flavor-create %s %s %s %s" % (cpu, ram, disk, storage),
            ]

    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            "/etc/init.d/snf-dispatcher restart",
            ]


class VNC(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "snf-vncauthproxy"
        ]

    def prepare(self):
        return ["mkdir -p /var/lib/vncauthproxy"]

    def configure(self):
        return [
            ("/var/lib/vncauthproxy/users", {}, {})
            ]

    def initialize(self):
        user = self.env.env.synnefo_user
        passwd = self.env.env.synnefo_vnc_passwd
        #TODO: run vncauthproxy-passwd
        return []

    def restart(self):
        return [
            "/etc/init.d/vncauthproxy restart"
            ]


class Kamaki(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "python-progress",
        "kamaki",
        ]

    def initialize(self):
        url = "https://%s/astakos/identity/v2.0" % self.env.env.accounts.fqdn
        token = self.env.user_auth_token
        return [
            "kamaki config set cloud.default.url %s" % url,
            "kamaki config set cloud.default.token %s" % token,
            "kamaki container create images",
            ]

    def fetch_image(self):
        url = self.env.env.debian_base_url
        image = "debian_base.diskdump"
        return [
            "wget %s -O /tmp/%s" % (url, image)
            ]

    def upload_image(self):
        image = "debian_base.diskdump"
        return [
            "kamaki file upload --container images /tmp/%s %s" % (image, image)
            ]

    def register_image(self):
        image = "debian_base.diskdump"
        image_location = "/images/%s" % image
        cmd = """
        kamaki image register --name "Debian Base" --location {0} \
              --public --disk-format=diskdump \
              --property OSFAMILY=linux --property ROOT_PARTITION=1 \
              --property description="Debian Squeeze Base System" \
              --property size=450M --property kernel=2.6.32 \
              --property GUI="No GUI" --property sortorder=1 \
              --property USERS=root --property OS=debian
        """.format(image_location)
        return [
            "sleep 5",
            cmd
            ]


class Burnin(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "kamaki",
        "snf-tools",
        ]


class Collectd(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "collectd",
        ]

    def configure(self):
        return [
            ("/etc/collectd/collectd.conf", {}, {}),
            ]

    def restart(self):
        return [
            "/etc/init.d/collectd restart",
            ]


class Stats(SynnefoComponent):
    REQUIRED_PACKAGES = [
        "snf-stats-app",
        ]

    def prepare(self):
        return [
            "mkdir -p /var/cache/snf-stats-app/",
            "chown www-data:www-data /var/cache/snf-stats-app/",
            ]

    def configure(self):
        r1 = {
            "STATS": self.env.env.stats.fqdn,
            }
        return [
            ("/etc/synnefo/stats.conf", r1, {}),
            ("/etc/collectd/synnefo-stats.conf", r1, {}),
            ]

    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            "/etc/init.d/apache2 restart",
            ]


class GanetiCollectd(SynnefoComponent):
    def configure(self):
        r1 = {
            "STATS": self.env.env.stats.fqdn,
            }
        return [
            ("/etc/collectd/passwd", {}, {}),
            ("/etc/collectd/synnefo-ganeti.conf", r1, {}),
            ]
