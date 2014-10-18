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

import re
import datetime
import simplejson
import copy
import os
from snfdeploy import base
from snfdeploy import config
from snfdeploy import constants
from snfdeploy import context
from snfdeploy.lib import FQDN, evaluate


_USER_INFO_RE = lambda x: \
    re.compile(r"(\d+)[ |]*(\S+)[ |]*(\S+)[ |]*%s.*" % x, re.M)
_USER_INFO = ["user_id", "user_auth_token", "user_uuid"]

_SERVICE_INFO_RE = lambda x: re.compile(r"(\d+)[ ]*%s[ ]*(\S+)" % x, re.M)
_SERVICE_INFO = ["service_id", "service_token"]

_BACKEND_INFO_RE = lambda x: re.compile(r"(\d+)[ ]*%s.*" % x, re.M)
_BACKEND_INFO = ["backend_id"]

_VOLUME_INFO_RE = lambda x: re.compile(r"(\d+)[ ]*%s.*" % x, re.M)
_VOLUME_INFO = ["volume_type_id"]


# Helper decorator that wraps get_* methods of certain Components
# Those methods take one argument; the identity (mail, service, backend)
# to look for. It parses the output of those methods and updates the
# context's keys with the matched groups.
def parse(regex, keys):
    def wrap(f):
        def wrapped_f(cl, what):
            result = f(cl, what)
            match = regex(what).search(result)
            if config.dry_run:
                evaluate(context, **dict(zip(keys, ["dummy"] * len(keys))))
            elif match:
                evaluate(context, **dict(zip(keys, match.groups())))
            else:
                raise BaseException("Cannot parse info for %s" % what)
        return wrapped_f
    return wrap


def update_admin(fn):
    """ Initializes the admin roles for each component

    Initialize the admin roles (NS, Astakos, Cyclades, etc.) and make them
    available under self.NS, self.ASTAKOS, etc. These have the same execution
    context of the current components besides the target node which gets
    derived from the corresponding config.

    """
    def wrapper(*args, **kwargs):
        """If used as decorator of a class method first argument is self."""
        cl = args[0]
        ctx = copy.deepcopy(cl.ctx)
        ctx.admin_service = cl.service
        ctx.admin_cluster = cl.cluster
        ctx.admin_node = cl.node
        ctx.admin_fqdn = cl.fqdn
        cl.NS = NS(node=ctx.ns.node, ctx=ctx)
        cl.NFS = NFS(node=ctx.nfs.node, ctx=ctx)
        cl.DB = DB(node=ctx.db.node, ctx=ctx)
        cl.ASTAKOS = Astakos(node=ctx.astakos.node, ctx=ctx)
        cl.CYCLADES = Cyclades(node=ctx.cyclades.node, ctx=ctx)
        cl.ADMIN = Admin(node=ctx.admin.node, ctx=ctx)
        cl.CLIENT = Client(node=ctx.client.node, ctx=ctx)
        return fn(*args, **kwargs)
    return wrapper


def update_cluster_admin(fn):
    """ Initializes the cluster admin roles for each component

    Finds the master role for the corresponding cluster

    """
    def wrapper(*args, **kwargs):
        """If used as decorator of a class method first argument is self."""
        cl = args[0]
        ctx = copy.deepcopy(cl.ctx)
        ctx.admin_cluster = cl.cluster
        cl.MASTER = Master(node=ctx.master.node, ctx=ctx)
        return fn(*args, **kwargs)
    return wrapper


def export_and_import_service(fn):
    """ Export and import synnefo service

    Used in Astakos, Pithos, and Cyclades service admin_post method

    """
    def wrapper(*args, **kwargs):
        cl = args[0]
        f = config.jsonfile
        cl.export_service()
        cl.get(f, f + ".local")
        cl.ASTAKOS.put(f + ".local", f)
        cl.ASTAKOS.import_service()
        return fn(*args, **kwargs)
    return wrapper


def cert_override(fn):
    """ Create all needed entries for cert_override.txt file

    Append them in a tmp file and upload them to client node

    """
    def wrapper(*args, **kwargs):
        cl = args[0]
        f = "/tmp/" + constants.CERT_OVERRIDE + "_" + cl.service
        for domain in [cl.node.domain, cl.node.cname, cl.node.ip]:
            cmd = """
python /root/firefox_cert_override.py {0} {1}:443 >> {2}
""".format(constants.CERT_PATH, domain, f)
            cl.run(cmd)
        cl.get(f, f + ".local")
        cl.CLIENT.put(f + ".local", f)
        return fn(*args, **kwargs)
    return wrapper


# ########################## Components ############################

# A Component() gets initialized with an execution context that is a
# configuration snapshot of the target setup, cluster and node. A
# component implements the following helper methods: check, install,
# prepare, configure, restart, initialize, and test. All those methods
# will be executed on the target node with this order during setup.
#
# Additionally each Component class implements admin_pre, and
# admin_post methods which invoke actions on different components on
# the same execution context before and after installation. For
# example before a backend gets installed, its FQDN must resolve to
# the master floating IP, so we have to run some actions on the ns
# node and after installation we must add it to cyclades (snf-manage
# backend-add on the cyclades node).
#
# Component() inherits ComponentRunner() which practically exports the
# setup() method. This will first check if the required components are
# installed, will install them if not and update the status of target
# node.
#
# ComponentRunner() inherits FabricRunner() which practically wraps
# basic fabric commands (put, get, run) with the correct execution
# environment.
#
# Each component gets initialized with an execution context and uses
# the config module for accessing global wide options. The context
# provides node, cluster, and setup related info.

class HW(base.Component):
    @base.check_if_testing
    def _configure(self):
        r1 = {
            "date": str(datetime.datetime.today()),
            }
        return [
            ("/etc/sysctl.d/disable-ipv6.conf", r1, {})
            ]

    @base.run_cmds
    @base.check_if_testing
    def initialize(self):
        return [
            "sysctl -f /etc/sysctl.d/disable-ipv6.conf",
            ]

    @base.run_cmds
    def test(self):
        return [
            "ping -c 1 %s" % self.node.ip,
            "ping -c 1 www.google.com",
            "apt-get update",
            ]


class SSH(base.Component):
    @base.run_cmds
    def prepare(self):
        return [
            "mkdir -p /root/.ssh",
            "for f in $(ls /root/.ssh/*); do cp $f $f.bak ; done",
            "echo StrictHostKeyChecking no >> /etc/ssh/ssh_config",
            ]

    def _configure(self):
        files = [
            "authorized_keys", "id_dsa", "id_dsa.pub", "id_rsa", "id_rsa.pub"
            ]
        ssh = [("/root/.ssh/%s" % f, {}, {"mode": 0600}) for f in files]
        return ssh

    @base.run_cmds
    def initialize(self):
        f = "/root/.ssh/authorized_keys"
        return [
            "test -e {0}.bak && cat {0}.bak >> {0} || true".format(f)
            ]

    @base.run_cmds
    def test(self):
        return ["ssh %s date" % self.node.ip]


class DNS(base.Component):
    @update_admin
    def admin_pre(self):
        self.NS.update_ns()

    @base.run_cmds
    def prepare(self):
        return [
            "chattr -i /etc/resolv.conf",
            "sed -i 's/^127.*$/127.0.0.1 localhost/g' /etc/hosts",
            "echo %s > /etc/hostname" % self.node.hostname,
            "hostname %s" % self.node.hostname
            ]

    def _configure(self):
        r1 = {
            "date": str(datetime.datetime.today()),
            "domain": self.node.domain,
            "ns_node_ip": self.ctx.ns.ip,
            }
        resolv = [
            ("/etc/resolv.conf", r1, {})
            ]
        return resolv

    @base.run_cmds
    def initialize(self):
        return ["chattr +i /etc/resolv.conf"]


class DDNS(base.Component):
    REQUIRED_PACKAGES = [
        "dnsutils",
        ]

    @base.run_cmds
    def prepare(self):
        return [
            "mkdir -p /root/ddns/"
            ]

    def _configure(self):
        return [
            ("/root/ddns/" + k, {}, {}) for k in config.ddns_keys
            ]


class NS(base.Component):
    REQUIRED_PACKAGES = [
        "bind9",
        ]

    alias = constants.NS

    def required_components(self):
        return [HW, SSH, DDNS]

    def _nsupdate(self, cmd):
        ret = """
nsupdate -k {0} > /dev/null <<EOF || true
server {1}
{2}
send
EOF
""".format(config.ddns_private_key, self.ctx.ns.ip, cmd)
        return ret

    @base.run_cmds
    def update_ns(self, info=None):
        if not info:
            info = self.ctx.admin_fqdn
        return [
            self._nsupdate("update add %s" % info.arecord),
            self._nsupdate("update add %s" % info.ptrrecord),
            self._nsupdate("update add %s" % info.cnamerecord),
            ]

    def add_qa_instances(self):
        instances = [
            ("xen-test-inst1", "1.2.3.4"),
            ("xen-test-inst2", "1.2.3.5"),
            ("xen-test-inst3", "1.2.3.6"),
            ("xen-test-inst4", "1.2.3.7"),
            ]
        for name, ip in instances:
            info = {
                "name": name,
                "ip": ip,
                "domain": self.node.domain
                }
            node_info = FQDN(**info)
            self.update_ns(node_info)

    @base.run_cmds
    def prepare(self):
        return [
            "mkdir -p /etc/bind/zones",
            "chmod g+w /etc/bind/zones",
            "mkdir -p /etc/bind/rev",
            "chmod g+w /etc/bind/rev",
            ]

    def _configure(self):
        d = self.node.domain
        ip = self.node.ip
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
             {"node_ips": ";".join(self.ctx.all_ips)}, {}),
            ("/root/ddns/ddns.key", {}, {"remote": "/etc/bind/ddns.key"}),
            ]

    @base.run_cmds
    def restart(self):
        return ["/etc/init.d/bind9 restart"]


class APT(base.Component):
    """ Setup apt repos and check fqdns """
    REQUIRED_PACKAGES = ["curl"]

    @base.run_cmds
    def prepare(self):
        return [
            "echo 'APT::Install-Suggests \"false\";' >> /etc/apt/apt.conf",
            "curl -k https://dev.grnet.gr/files/apt-grnetdev.pub | \
                apt-key add -",
            ]

    def _configure(self):
        return [
            ("/etc/apt/sources.list.d/synnefo.wheezy.list", {}, {})
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "apt-get update",
            ]


class MQ(base.Component):
    REQUIRED_PACKAGES = ["rabbitmq-server"]

    alias = constants.MQ

    def required_components(self):
        return [HW, SSH, DNS, APT]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()

    @base.run_cmds
    def check(self):
        return ["ping -c 1 %s" % self.node.cname]

    @base.run_cmds
    def initialize(self):
        u = config.synnefo_user
        p = config.synnefo_rabbitmq_passwd
        return [
            "rabbitmqctl add_user %s %s" % (u, p),
            "rabbitmqctl set_permissions %s \".*\" \".*\" \".*\"" % u,
            "rabbitmqctl delete_user guest",
            "rabbitmqctl set_user_tags %s administrator" % u,
            ]


class DB(base.Component):
    REQUIRED_PACKAGES = ["postgresql"]

    alias = constants.DB

    def required_components(self):
        return [HW, SSH, DNS, APT]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()

    @base.run_cmds
    def check(self):
        return ["ping -c 1 %s" % self.node.cname]

    @parse(_USER_INFO_RE, _USER_INFO)
    @base.run_cmds
    def get_user_info_from_db(self, user_email):
        cmd = """
cat > /tmp/psqlcmd <<EOF
select id, auth_token, uuid, email from auth_user, im_astakosuser \
where auth_user.id = im_astakosuser.user_ptr_id and auth_user.email = '{0}';
EOF

su - postgres -c  "psql -w -d snf_apps -f /tmp/psqlcmd"
""".format(user_email)

        return [cmd]

    @base.run_cmds
    def allow_db_access(self):
        user = "all"
        method = "md5"
        ip = self.ctx.admin_node.ip
        f = "/etc/postgresql/*/main/pg_hba.conf"
        cmd1 = "echo host all %s %s/32 %s >> %s" % \
            (user, ip, method, f)
        cmd2 = "sed -i 's/\(host.*127.0.0.1.*\)md5/\\1trust/' %s" % f
        return [cmd1, cmd2]

    def _configure(self):
        u = config.synnefo_user
        p = config.synnefo_db_passwd
        replace = {"synnefo_user": u, "synnefo_db_passwd": p}
        return [
            ("/tmp/db-init.psql", replace, {}),
            ]

    @base.check_if_testing
    def make_db_fast(self):
        f = "/etc/postgresql/*/main/postgresql.conf"
        opts = "fsync=off\nsynchronous_commit=off\nfull_page_writes=off\n"
        return ["""echo -e "%s" >> %s""" % (opts, f)]

    @base.run_cmds
    def prepare(self):
        f = "/etc/postgresql/*/main/postgresql.conf"
        ret = ["""echo "listen_addresses = '*'" >> %s""" % f]
        return ret + self.make_db_fast()

    @base.run_cmds
    def initialize(self):
        script = "/tmp/db-init.psql"
        cmd = "su - postgres -c \"psql -w -f %s\" " % script
        return [cmd]

    @base.run_cmds
    def restart(self):
        return ["/etc/init.d/postgresql restart"]

    @base.run_cmds
    def destroy_db(self):
        return [
            """su - postgres -c ' psql -w -c "drop database snf_apps" '""",
            """su - postgres -c ' psql -w -c "drop database snf_pithos" '"""
            ]


class VMC(base.Component):

    def extra_components(self):
        if self.cluster.synnefo:
            return [
                Image, GTools, GanetiCollectd,
                PithosBackend, ExtStorage, Archip, ArchipGaneti
                ]
        else:
            return [ExtStorage, Archip, ArchipGaneti]

    def required_components(self):
        return [
            HW, SSH, DNS, DDNS, APT, Mount, LVM, DRBD, Ganeti, Network,
            ] + self.extra_components()

    @update_cluster_admin
    def admin_post(self):
        self.MASTER.add_node(self.node)
        self.MASTER.enable_lvm()
        self.MASTER.enable_drbd()


class LVM(base.Component):
    REQUIRED_PACKAGES = [
        "lvm2",
        ]

    @base.run_cmds
    def initialize(self):
        extra_disk_dev = self.node.extra_disk
        extra_disk_file = "/disk"
        # If extra disk found use it
        # else create a raw file and losetup it
        cmd = """
if [ -b "{0}" ]; then
  pvcreate {0} && vgcreate {2} {0}
else
  truncate -s {3} {1}
  loop_dev=$(losetup -f --show {1})
  pvcreate $loop_dev
  vgcreate {2} $loop_dev
fi
""".format(extra_disk_dev, extra_disk_file,
           self.cluster.vg, self.cluster.vg_size)

        return [cmd]


class DRBD(base.Component):
    REQUIRED_PACKAGES = [
        "drbd8-utils",
        ]

    def _configure(self):
        return [
            ("/etc/modprobe.d/drbd.conf", {}, {}),
            ]

    def prepare(self):
        return [
            "echo drbd >> /etc/modules",
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "modprobe -rv drbd || true",
            "modprobe -v drbd",
            ]


class Ganeti(base.Component):
    REQUIRED_PACKAGES = [
        "qemu-kvm",
        "python-bitarray",
        "bridge-utils",
        "snf-ganeti",
        "ganeti2",
        "ganeti-instance-debootstrap"
        ]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()

    @base.run_cmds
    def check(self):
        commands = [
            "getent hosts %s | grep -v ^127" % self.node.hostname,
            "hostname -f | grep %s" % self.node.fqdn,
            ]
        return commands

    def _configure(self):
        r = {
            "SHARED_GANETI_DIR": config.ganeti_dir,
            }
        return [
            ("/etc/ganeti/file-storage-paths", r, {}),
            ("/etc/default/ganeti-instance-debootstrap", {}, {}),
            ]

    def _prepare_net_infra(self):
        br = config.common_bridge
        return [
            "brctl addbr {0}; ip link set {0} up".format(br)
            ]

    @base.run_cmds
    def prepare(self):
        return [
            "mkdir -p %s/file-storage/" % config.ganeti_dir,
            "mkdir -p %s/shared-file-storage/" % config.ganeti_dir,
            "sed -i 's/^127.*$/127.0.0.1 localhost/g' /etc/hosts",
            ] + self._prepare_net_infra()

    @base.run_cmds
    def restart(self):
        return ["/etc/init.d/ganeti restart"]


class Master(base.Component):

    @property
    def fqdn(self):
        return self.cluster

    def required_components(self):
        return [
            HW, SSH, DNS, DDNS, APT, Mount, Ganeti
            ]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()

    @base.run_cmds
    def check(self):
        commands = [
            "host %s" % self.cluster.fqdn,
            ]
        return commands

    @base.run_cmds
    def add_qa_rapi_user(self):
        cmd = """
echo ganeti-qa qa_example_passwd write >> /var/lib/ganeti/rapi/users
"""
        return [cmd]

    def _add_rapi_user(self):
        user = config.synnefo_user
        passwd = config.synnefo_rapi_passwd
        x = "%s:Ganeti Remote API:%s" % (user, passwd)

        cmd = """
cat >> /var/lib/ganeti/rapi/users <<EOF
%s {HA1}$(echo -n %s | openssl md5 | sed 's/^.* //') write
EOF
""" % (user, x)

        return [cmd]

    @base.run_cmds
    def add_node(self, info):
        add = """
gnt-node list {0} || gnt-node add --no-ssh-key-check {0}
""".format(info.fqdn)

        mod_vm = """
gnt-node modify --vm-capable=yes {0}
""".format(info.fqdn)

        mod_master = """
gnt-node modify --master-capable=yes {0}
""".format(info.fqdn)

        return [add, mod_vm, mod_master]

    @base.run_cmds
    def enable_lvm(self):
        vg = self.cluster.vg
        return [
            # This is needed because MIN_VG_SIZE is constant and set to 20G
            # and cluster modify --vg-name may result to:
            # volume group 'ganeti' too small
            # But this check is made only ff a vm-capable node is found
            "gnt-cluster modify --enabled-disk-templates file,ext,plain \
                                --vg-name=%s" % vg,
            "gnt-cluster modify --ipolicy-disk-template file,ext,plain",
            ]

    @base.run_cmds
    def enable_drbd(self):
        vg = self.cluster.vg
        return [
            "gnt-cluster modify --enabled-disk-templates file,ext,plain,drbd \
                                --drbd-usermode-helper=/bin/true",
            "gnt-cluster modify --ipolicy-disk-template file,ext,plain,drbd",
            "gnt-cluster modify --disk-parameters=drbd:metavg=%s" % vg,
            "gnt-group modify --disk-parameters=drbd:metavg=%s default" % vg,
            ]

    @base.run_cmds
    def initialize(self):
        std = "cpu-count=1,disk-count=1,disk-size=1024"
        std += ",memory-size=128,nic-count=1,spindle-use=1"

        bound_min = "cpu-count=1,disk-count=1,disk-size=512"
        bound_min += ",memory-size=128,nic-count=0,spindle-use=1"

        bound_max = "cpu-count=8,disk-count=16,disk-size=1048576"
        bound_max += ",memory-size=32768,nic-count=8,spindle-use=12"

        init = """
gnt-cluster init --enabled-hypervisors=kvm \
    --nic-parameters link={0},mode=bridged \
    --master-netdev {1} \
    --default-iallocator hail \
    --hypervisor-parameters kvm:kernel_path=,vnc_bind_address=0.0.0.0 \
    --no-ssh-init --no-etc-hosts \
    --ipolicy-std-specs {2} \
    --ipolicy-bounds-specs min:{3}/max:{4} \
    --enabled-disk-templates file,ext \
    {5}
        """.format(config.common_bridge, self.cluster.netdev,
                   std, bound_min, bound_max, self.cluster.fqdn)

        modify = "gnt-node modify --vm-capable=no %s" % self.node.fqdn

        return [init, modify] + self._add_rapi_user()

    @base.run_cmds
    def restart(self):
        return ["/etc/init.d/ganeti restart"]

    @update_admin
    @update_cluster_admin
    def admin_post(self):
        if self.cluster.synnefo:
            self.CYCLADES._debug("Adding backend: %s" % self.cluster.fqdn)
            self.CYCLADES.add_backend()
            self.CYCLADES.list_backends(self.cluster.fqdn)
            self.CYCLADES.undrain_backend()


class Image(base.Component):
    REQUIRED_PACKAGES = [
        "snf-image",
        ]

    @base.run_cmds
    def check(self):
        return ["mkdir -p %s" % config.images_dir]

    @base.run_cmds
    def prepare(self):
        url = config.debian_base_url
        d = config.images_dir
        image = "debian_base.diskdump"
        return [
            "test -e /tmp/%s || wget -4 %s -O /tmp/%s" % (image, url, image),
            "cp /tmp/%s %s/%s" % (image, d, image),
            "mv /etc/default/snf-image /etc/default/snf-image.orig",
            ]

    def _configure(self):
        tmpl = "/etc/default/snf-image"
        replace = {
            "synnefo_user": config.synnefo_user,
            "synnefo_db_passwd": config.synnefo_db_passwd,
            "db_node": self.ctx.db.cname,
            "image_dir": config.images_dir,
            }
        return [(tmpl, replace, {})]

    @base.run_cmds
    def initialize(self):
        # This is done during postinstall phase
        # snf-image-update-helper -y
        return []


class GTools(base.Component):
    REQUIRED_PACKAGES = [
        "snf-cyclades-gtools",
        ]

    @base.run_cmds
    def check(self):
        return ["ping -c1 %s" % self.ctx.mq.cname]

    @base.run_cmds
    def prepare(self):
        return [
            "sed -i 's/false/true/' /etc/default/snf-ganeti-eventd",
            "chown -R root:archipelago /etc/synnefo/",
            ]

    def _configure(self):
        tmpl = "/etc/synnefo/gtools.conf"
        replace = {
            "synnefo_user": config.synnefo_user,
            "synnefo_rabbitmq_passwd": config.synnefo_rabbitmq_passwd,
            "mq_node": self.ctx.mq.cname,
            }
        return [(tmpl, replace, {})]

    @base.run_cmds
    def restart(self):
        return ["/etc/init.d/snf-ganeti-eventd restart"]


class Network(base.Component):
    REQUIRED_PACKAGES = [
        "python-nfqueue",
        "snf-network",
        "nfdhcpd",
        ]

    def _configure(self):
        r1 = {
            "ns_node_ip": self.ctx.ns.ip
            }
        r2 = {
            "common_bridge": config.common_bridge,
            "public_iface": self.node.public_iface,
            "subnet": config.synnefo_public_network_subnet,
            "gateway": config.synnefo_public_network_gateway,
            "router_ip": self.ctx.router.ip,
            "node_ip": self.node.ip,
            }
        r3 = {
            "domain": self.node.domain,
            "server": self.ctx.ns.ip,
            "keyfile": config.ddns_private_key,
            }

        return [
            ("/etc/nfdhcpd/nfdhcpd.conf", r1, {}),
            ("/etc/rc.local", r2, {"mode": 0755}),
            ("/etc/default/snf-network", r3, {}),
            ]

    @base.run_cmds
    def initialize(self):
        return ["/etc/init.d/rc.local start"]

    @base.run_cmds
    def restart(self):
        return ["/etc/init.d/nfdhcpd restart"]


class Apache(base.Component):
    REQUIRED_PACKAGES = [
        "apache2",
        "python-openssl",
        ]

    @base.run_cmds
    def prepare(self):
        return [
            "a2enmod ssl", "a2enmod rewrite", "a2dissite default",
            "a2enmod headers",
            "a2enmod proxy_http", "a2dismod autoindex",
            ]

    def _configure(self):
        r1 = {"HOST": self.node.fqdn}
        return [
            ("/etc/apache2/sites-available/synnefo", r1, {}),
            ("/etc/apache2/sites-available/synnefo-ssl", r1, {}),
            ("/root/firefox_cert_override.py", {}, {})
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "a2ensite synnefo", "a2ensite synnefo-ssl",
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/apache2 restart",
            ]


class Gunicorn(base.Component):
    REQUIRED_PACKAGES = [
        "python-gevent",
        "gunicorn",
        ]

    @base.run_cmds
    def prepare(self):
        return [
            "chown root:www-data /var/log/gunicorn",
            ]

    def _configure(self):
        r1 = {"HOST": self.node.fqdn}
        return [
            ("/etc/gunicorn.d/synnefo", r1, {}),
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]


class Common(base.Component):
    REQUIRED_PACKAGES = [
        "ntp",
        "snf-common",
        "snf-branding",
        ]

    def _configure(self):
        r1 = {
            "EMAIL_SUBJECT_PREFIX": self.node.hostname,
            "domain": self.node.domain,
            "HOST": self.node.fqdn,
            "MAIL_DIR": config.mail_dir,
            }
        return [
            ("/etc/synnefo/common.conf", r1, {}),
            ]

    @base.run_cmds
    def initialize(self):
        return ["mkdir -p {0}; chmod 777 {0}".format(config.mail_dir)]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]


class Webproject(base.Component):
    REQUIRED_PACKAGES = [
        "python-psycopg2",
        "python-astakosclient",
        "snf-django-lib",
        "snf-webproject",
        ]

    @base.run_cmds
    def check(self):
        return ["ping -c1 %s" % self.ctx.db.cname]

    def _configure(self):
        r1 = {
            "synnefo_user": config.synnefo_user,
            "synnefo_db_passwd": config.synnefo_db_passwd,
            "db_node": self.ctx.db.cname,
            "domain": self.node.domain,
            "webproject_secret": config.webproject_secret,
            }
        return [
            ("/etc/synnefo/webproject.conf", r1, {}),
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]


class Astakos(base.Component):
    REQUIRED_PACKAGES = [
        "snf-astakos-app",
        ]

    alias = constants.ASTAKOS
    service = constants.ASTAKOS

    def required_components(self):
        return [HW, SSH, DNS, APT, Apache, Gunicorn, Common, Webproject]

    @base.run_cmds
    def setup_user(self):
        self._debug("Setting up user")
        return self._set_default_quota() + \
            self._add_user() + self._activate_user()

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()
        self.DB.allow_db_access()
        self.DB.restart()

    @property
    def conflicts(self):
        return [CMS]

    @base.run_cmds
    def export_service(self):
        f = config.jsonfile
        return [
            "snf-manage service-export-astakos > %s" % f
            ]

    @base.run_cmds
    def import_service(self):
        f = config.jsonfile
        return [
            "snf-manage service-import --json=%s" % f
            ]

    @base.run_cmds
    def set_astakos_default_quota(self):
        cmd = "snf-manage resource-modify"
        return [
            "%s --system-default 2 astakos.pending_app" % cmd,
            "%s --project-default 0 astakos.pending_app" % cmd,
            ]

    @base.run_cmds
    def set_cyclades_default_quota(self):
        cmd = "snf-manage resource-modify"
        return [
            "%s --system-default 4 cyclades.vm" % cmd,
            "%s --system-default 40G cyclades.disk" % cmd,
            "%s --system-default 16G cyclades.total_ram" % cmd,
            "%s --system-default 8G cyclades.ram" % cmd,
            "%s --system-default 32 cyclades.total_cpu" % cmd,
            "%s --system-default 16 cyclades.cpu" % cmd,
            "%s --system-default 4 cyclades.network.private" % cmd,
            "%s --system-default 4 cyclades.floating_ip" % cmd,
            "%s --project-default 0 cyclades.vm" % cmd,
            "%s --project-default 0 cyclades.disk" % cmd,
            "%s --project-default inf cyclades.total_ram" % cmd,
            "%s --project-default 0 cyclades.ram" % cmd,
            "%s --project-default inf cyclades.total_cpu" % cmd,
            "%s --project-default 0 cyclades.cpu" % cmd,
            "%s --project-default 0 cyclades.network.private" % cmd,
            "%s --project-default 0 cyclades.floating_ip" % cmd,
            ]

    @base.run_cmds
    def set_pithos_default_quota(self):
        cmd = "snf-manage resource-modify"
        return [
            "%s --system-default 40G pithos.diskspace" % cmd,
            "%s --project-default 0 pithos.diskspace" % cmd,
            ]

    @base.run_cmds
    def modify_all_quota(self):
        cmd = "snf-manage project-modify --all-system-projects --limit"
        return [
            "%s pithos.diskspace 40G 40G" % cmd,
            "%s astakos.pending_app 2 2" % cmd,
            "%s cyclades.vm 4 4" % cmd,
            "%s cyclades.disk 40G 40G" % cmd,
            "%s cyclades.total_ram 16G 16G" % cmd,
            "%s cyclades.ram 8G 8G" % cmd,
            "%s cyclades.total_cpu 32 32" % cmd,
            "%s cyclades.cpu 16 16" % cmd,
            "%s cyclades.network.private 4 4" % cmd,
            "%s cyclades.floating_ip 4 4" % cmd,
            ]

    @parse(_SERVICE_INFO_RE, _SERVICE_INFO)
    @base.run_cmds
    def get_services(self, service):
        return [
            "snf-manage component-list -o id,name,token"
            ]

    def _configure(self):
        r1 = {
            "ACCOUNTS": self.ctx.astakos.cname,
            "domain": self.node.domain,
            "CYCLADES": self.ctx.cyclades.cname,
            "PITHOS": self.ctx.pithos.cname,
            }
        return [
            ("/etc/synnefo/astakos.conf", r1, {}),
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "snf-manage syncdb --noinput",
            "snf-manage migrate im --delete-ghost-migrations",
            "snf-manage migrate quotaholder_app",
            "snf-manage migrate oa2",
            "snf-manage loaddata groups",
            ] + self._astakos_oa2() + self._astakos_register_components()

    def _astakos_oa2(self):
        secret = config.oa2_secret
        view = "https://%s/pithos/ui/view" % self.ctx.pithos.cname
        cmd = "snf-manage oauth2-client-add pithos-view \
                  --secret=%s --is-trusted --url %s || true" % (secret, view)
        return [cmd]

    def _astakos_register_components(self):
        # base urls
        cbu = "https://%s/cyclades" % self.ctx.cyclades.cname
        pbu = "https://%s/pithos" % self.ctx.pithos.cname
        abu = "https://%s/astakos" % self.ctx.astakos.cname
        cmsurl = "https://%s/home" % self.ctx.cms.cname

        cmd = "snf-manage component-add"
        h = "%s home --base-url %s --ui-url %s" % (cmd, cmsurl, cmsurl)
        c = "%s cyclades --base-url %s --ui-url %s/ui" % (cmd, cbu, cbu)
        p = "%s pithos --base-url %s --ui-url %s/ui" % (cmd, pbu, pbu)
        a = "%s astakos --base-url %s --ui-url %s/ui" % (cmd, abu, abu)

        return [h, c, p, a]

    @base.run_cmds
    def add_user(self):
        info = (
            config.user_passwd,
            config.user_email,
            config.user_name,
            config.user_lastname,
            )
        cmd = "snf-manage user-add --password %s %s %s %s" % info
        return [cmd]

    @update_admin
    @base.run_cmds
    def activate_user(self):
        self.DB.get_user_info_from_db(config.user_email)
        user_id = context.user_id
        return [
            "snf-manage user-modify --verify %s" % user_id,
            "snf-manage user-modify --accept %s" % user_id,
            ]

    @update_admin
    @export_and_import_service
    @cert_override
    def admin_post(self):
        self.set_astakos_default_quota()


class CMS(base.Component):
    REQUIRED_PACKAGES = [
        "snf-cloudcms"
        ]

    alias = constants.CMS
    service = constants.CMS

    def required_components(self):
        return [HW, SSH, DNS, APT, Apache, Gunicorn, Common, Webproject]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()
        self.DB.allow_db_access()
        self.DB.restart()

    @property
    def conflicts(self):
        return [Astakos, Pithos, Cyclades]

    def _configure(self):
        r1 = {
            "ACCOUNTS": self.ctx.astakos.cname
            }
        r2 = {
            "DOMAIN": self.node.domain
            }
        return [
            ("/etc/synnefo/cms.conf", r1, {}),
            ("/tmp/sites.json", r2, {}),
            ("/tmp/page.json", {}, {}),
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "snf-manage syncdb",
            "snf-manage migrate --delete-ghost-migrations",
            "snf-manage loaddata /tmp/sites.json",
            "snf-manage loaddata /tmp/page.json",
            "snf-manage createsuperuser --username=admin \
                  --email=admin@%s --noinput" % self.node.domain,
            ]

    @base.run_cmds
    def restart(self):
        return ["/etc/init.d/gunicorn restart"]

    @update_admin
    @cert_override
    def admin_post(self):
        pass


class Mount(base.Component):
    REQUIRED_PACKAGES = [
        "nfs-common"
        ]

    @update_admin
    def admin_pre(self):
        self.NFS.update_exports()
        self.NFS.restart()

    @property
    def conflicts(self):
        return [NFS]

    @base.run_cmds
    def prepare(self):
        fstab = """
cat >> /etc/fstab <<EOF
{0}:{1} {1}  nfs defaults,rw,noatime,rsize=131072,wsize=131072 0 0
EOF
""".format(self.ctx.nfs.cname, config.shared_dir)

        return [
            "mkdir -p %s" % config.shared_dir,
            "addgroup --gid 200 archipelago",
            "adduser --system --no-create-home \
              --gecos 'Archipelago user' --gid 200 archipelago",
            fstab,
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "mount %s" % config.shared_dir
            ]


class NFS(base.Component):
    REQUIRED_PACKAGES = [
        "rpcbind",
        "nfs-kernel-server"
        ]

    alias = constants.NFS

    def required_components(self):
        return [HW, SSH, DNS, APT]

    @property
    def conflicts(self):
        return [Mount]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()

    @base.run_cmds
    def prepare(self):
        return [
            "mkdir -p %s" % config.shared_dir,
            "mkdir -p %s" % config.images_dir,
            "mkdir -p %s" % config.ganeti_dir,
            "mkdir -p %s" % config.archip_dir,
            "addgroup --gid 200 archipelago",
            "adduser --system --no-create-home \
              --gecos 'Archipelago user' --gid 200 archipelago",
            "cd %s && mkdir {maps,blocks,locks}" % config.archip_dir,
            "cd %s && chown archipelago:archipelago {maps,blocks,locks}" % \
              config.archip_dir,
            "cd %s && chmod 770 {maps,blocks,locks}" % config.archip_dir,
            "cd %s && chmod g+s {maps,blocks,locks}" % config.archip_dir,
            ]

    @base.run_cmds
    def update_exports(self):
        fqdn = self.ctx.admin_node.fqdn
        cmd = """
grep {1} /etc/exports || cat >> /etc/exports <<EOF
{0} {1}(rw,async,no_subtree_check,no_root_squash)
EOF
""".format(config.shared_dir, fqdn)
        return [cmd]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/nfs-kernel-server restart",
            ]


class Pithos(base.Component):
    REQUIRED_PACKAGES = [
        "snf-pithos-app",
        "snf-pithos-webclient",
        ]

    alias = constants.PITHOS
    service = constants.PITHOS

    def required_components(self):
        return [
            HW, SSH, DNS, APT, Apache, Gunicorn, Common, Webproject,
            PithosBackend, Archip, ArchipSynnefo
            ]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()
        self.ASTAKOS.get_services(self.service)
        self.DB.allow_db_access()
        self.DB.restart()

    @property
    def conflicts(self):
        return [CMS]

    @base.run_cmds
    def export_service(self):
        f = config.jsonfile
        return [
            "snf-manage service-export-pithos > %s" % f
            ]

    @base.run_cmds
    def prepare(self):
        return [
            "chown -R root:archipelago /etc/synnefo/",
            ]

    def _configure(self):
        r1 = {
            "ACCOUNTS": self.ctx.astakos.cname,
            "PITHOS": self.ctx.pithos.cname,
            "db_node": self.ctx.db.cname,
            "synnefo_user": config.synnefo_user,
            "synnefo_db_passwd": config.synnefo_db_passwd,
            "PITHOS_SERVICE_TOKEN": context.service_token,
            "oa2_secret": config.oa2_secret,
            }
        r2 = {
            "ACCOUNTS": self.ctx.astakos.cname,
            "PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE": context.service_id,
            }

        return [
            ("/etc/synnefo/pithos.conf", r1, {}),
            ("/etc/synnefo/webclient.conf", r2, {}),
            ]

    @base.run_cmds
    def initialize(self):
        return ["pithos-migrate stamp head"]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]

    @update_admin
    @export_and_import_service
    @cert_override
    def admin_post(self):
        self.ASTAKOS.set_pithos_default_quota()


class PithosBackend(base.Component):
    REQUIRED_PACKAGES = [
        "snf-pithos-backend",
        "python-psycopg2",
        ]

    def _configure(self):
        r1 = {
            "db_node": self.ctx.db.cname,
            "synnefo_user": config.synnefo_user,
            "synnefo_db_passwd": config.synnefo_db_passwd,
            }

        return [
            ("/etc/synnefo/backend.conf", r1, {}),
            ]


class Cyclades(base.Component):
    REQUIRED_PACKAGES = [
        "memcached",
        "python-memcache",
        "snf-cyclades-app",
        ]

    alias = constants.CYCLADES
    service = constants.CYCLADES

    def required_components(self):
        return [
            HW, SSH, DNS, APT,
            Apache, Gunicorn, Common, Webproject, VNC, PithosBackend,
            Archip, ArchipSynnefo
            ]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()
        self.ASTAKOS.get_services(self.service)
        self.DB.allow_db_access()
        self.DB.restart()

    @property
    def conflicts(self):
        return [CMS]

    def _add_network(self):
        subnet = config.synnefo_public_network_subnet
        gw = config.synnefo_public_network_gateway
        ntype = config.synnefo_public_network_type
        link = config.common_bridge

        cmd = """
snf-manage network-create --subnet={0} --gateway={1} --public \
  --dhcp=True --flavor={2} --mode=bridged --link={3} --name=Internet \
  --floating-ip-pool=True
""".format(subnet, gw, ntype, link)

        return [cmd]

    @base.check_if_testing
    def _add_network6(self):
        subnet = "babe::/64"
        gw = "babe::1"
        ntype = config.synnefo_public_network_type
        link = config.common_bridge

        cmd = """
snf-manage network-create --subnet6={0} \
      --gateway6={1} --public --dhcp=True --flavor={2} --mode=bridged \
       --link={3} --name=IPv6PublicNetwork
""".format(subnet, gw, ntype, link)

        return [cmd]

    @base.run_cmds
    def export_service(self):
        f = config.jsonfile
        return [
            "snf-manage service-export-cyclades > %s" % f
            ]

    @parse(_BACKEND_INFO_RE, _BACKEND_INFO)
    @base.run_cmds
    def list_backends(self, cluster):
        return [
            "snf-manage backend-list"
            ]

    @base.run_cmds
    def add_backend(self):
        cluster = self.ctx.admin_cluster.fqdn
        user = config.synnefo_user
        passwd = config.synnefo_rapi_passwd
        return [
            "snf-manage backend-add --clustername=%s --user=%s --pass=%s" %
            (cluster, user, passwd)
            ]

    @base.run_cmds
    def undrain_backend(self):
        backend_id = context.backend_id
        return [
            "snf-manage backend-modify --drained=False %s" % str(backend_id)
            ]

    @base.run_cmds
    def prepare(self):
        return [
            "sed -i 's/false/true/' /etc/default/snf-dispatcher",
            "chown -R root:archipelago /etc/synnefo/",
            ]

    def _configure(self):
        r1 = {
            "ACCOUNTS": self.ctx.astakos.cname,
            "CYCLADES": self.ctx.cyclades.cname,
            "mq_node": self.ctx.mq.cname,
            "db_node": self.ctx.db.cname,
            "synnefo_user": config.synnefo_user,
            "synnefo_db_passwd": config.synnefo_db_passwd,
            "synnefo_rabbitmq_passwd": config.synnefo_rabbitmq_passwd,
            "common_bridge": config.common_bridge,
            "domain": self.node.domain,
            "CYCLADES_SERVICE_TOKEN": context.service_token,
            "STATS": self.ctx.stats.cname,
            "STATS_SECRET": config.stats_secret,
            "SYNNEFO_VNC_PASSWD": config.synnefo_vnc_passwd,
            # TODO: fix java issue with no signed jar
            "CYCLADES_NODE_IP": self.ctx.cyclades.ip,
            "CYCLADES_SECRET": config.cyclades_secret,
            "SHARED_GANETI_DIR": config.ganeti_dir,
            }
        return [
            ("/etc/synnefo/cyclades.conf", r1, {}),
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "snf-manage syncdb",
            "snf-manage migrate --delete-ghost-migrations",
            "snf-manage pool-create --type=mac-prefix \
              --base=aa:00:0 --size=65536",
            "snf-manage pool-create --type=bridge --base=prv --size=20",
            ] + self._add_network() + self._add_network6()

    @base.run_cmds
    def _create_flavor(self):
        cpu = config.flavor_cpu
        ram = config.flavor_ram
        disk = config.flavor_disk
        volume = context.volume_type_id
        return [
            "snf-manage flavor-create %s %s %s %s" % (cpu, ram, disk, volume),
            ]

    @base.run_cmds
    def _create_volume_type(self, template):
        cmd = """
snf-manage volume-type-create --name {0} --disk-template {0}
""".format(template)
        return [cmd]

    @parse(_VOLUME_INFO_RE, _VOLUME_INFO)
    @base.run_cmds
    def list_volume_types(self, template):
        return [
            "snf-manage volume-type-list -o id,disk_template --no-headers"
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            "/etc/init.d/snf-dispatcher restart",
            ]

    def create_flavors(self):
        templates = config.flavor_storage.split(",")
        for t in templates:
            self._create_volume_type(t)
            self.list_volume_types(t)
            self._create_flavor()

    @update_admin
    @export_and_import_service
    @cert_override
    def admin_post(self):
        self.create_flavors()
        self.ASTAKOS.set_cyclades_default_quota()


class VNC(base.Component):
    REQUIRED_PACKAGES = [
        "snf-vncauthproxy"
        ]

    @base.run_cmds
    def prepare(self):
        user = config.synnefo_user
        passwd = config.synnefo_vnc_passwd
        outdir = "/var/lib/vncauthproxy"
        users_file = "%s/users" % outdir
        return [
            "mkdir -p %s" % outdir,
            "cp /etc/ssl/certs/ssl-cert-snakeoil.pem %s/cert.pem" % outdir,
            "cp /etc/ssl/private/ssl-cert-snakeoil.key %s/key.pem" % outdir,
            "chown vncauthproxy:vncauthproxy %s/*.pem" % outdir,
            "vncauthproxy-passwd -p %s %s %s" % (passwd, users_file, user)
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/vncauthproxy restart"
            ]


class Admin(base.Component):
    REQUIRED_PACKAGES = [
        "python-django-eztables",
        "snf-admin-app"
        ]

    alias = constants.ADMIN
    service = constants.ADMIN

    def required_components(self):
        return [
            HW, SSH, DNS, APT,
            Apache, Gunicorn, Common, Webproject,
            ]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()
        self.DB.allow_db_access()
        self.DB.restart()

    @base.run_cmds
    @update_admin
    def prepare(self):
        f = "/etc/synnefo/astakos.conf"
        self.ASTAKOS.get(f, "/tmp/astakos.conf")
        self.put("/tmp/astakos.conf", f)
        f = "/etc/synnefo/cyclades.conf"
        self.CYCLADES.get(f, "/tmp/cyclades.conf")
        self.put("/tmp/cyclades.conf", f)
        return [
            "chown -R root:archipelago /etc/synnefo",
            ]

    def _configure(self):
        r1 = {
            "ADMIN": self.ctx.admin.cname,
        }
        return [
            ("/etc/synnefo/admin.conf", r1, {})
            ]

    @base.run_cmds
    def initialize(self):
        return [
            "snf-manage group-add admin"
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart"
            ]

    @base.run_cmds
    def make_user_admin_user(self):
        user_id = context.user_id
        return [
            "snf-manage user-modify %s --add-group=admin" % user_id
            ]

    @update_admin
    @cert_override
    def admin_post(self):
        pass


class Kamaki(base.Component):
    REQUIRED_PACKAGES = [
        "python-progress",
        "kamaki",
        ]

    @update_admin
    def admin_pre(self):
        self.ASTAKOS.add_user()
        self.ASTAKOS.activate_user()
        self.DB.get_user_info_from_db(config.user_email)
        self.ADMIN.make_user_admin_user()

    @base.run_cmds
    def prepare(self):
        cmd = """
cat >> /etc/ca-certificates.conf <<EOF

# Deploy local certificate
local.org/snakeoil.crt
EOF
"""
        return [
            "mkdir -p /usr/share/ca-certificates/local.org",
            "cp /etc/ssl/certs/ssl-cert-snakeoil.pem \
                /usr/share/ca-certificates/local.org/snakeoil.crt",
            cmd,
            "update-ca-certificates",
            ]

    @base.run_cmds
    def initialize(self):
        url = "https://%s/astakos/identity/v2.0" % self.ctx.astakos.cname
        token = context.user_auth_token
        return [
            "kamaki config set cloud.default.url %s" % url,
            "kamaki config set cloud.default.token %s" % token,
            "kamaki container create images",
            ]

    def _fetch_image(self):
        url = config.debian_base_url
        image = "debian_base.diskdump"
        return [
            "test -e /tmp/%s || wget -4 %s -O /tmp/%s" % (image, url, image)
            ]

    def _upload_image(self):
        image = "debian_base.diskdump"
        return [
            "kamaki file upload --container images /tmp/%s %s" % (image, image)
            ]

    def _register_image(self):
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

    @base.run_cmds
    def test(self):
        return self._fetch_image() + self._upload_image() + \
            self._register_image()


class Burnin(base.Component):
    REQUIRED_PACKAGES = [
        "snf-tools",
        ]


class Collectd(base.Component):
    REQUIRED_PACKAGES = [
        "collectd",
        ]

    def _configure(self):
        return [
            ("/etc/collectd/collectd.conf", {}, {}),
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/collectd restart",
            ]


class Stats(base.Component):
    REQUIRED_PACKAGES = [
        "snf-stats-app",
        ]

    alias = constants.STATS

    def required_components(self):
        return [
            HW, SSH, DNS, APT,
            Apache, Gunicorn, Common, Webproject, Collectd
            ]

    @update_admin
    def admin_pre(self):
        self.NS.update_ns()

    @base.run_cmds
    def prepare(self):
        return [
            "mkdir -p /var/cache/snf-stats-app/",
            "chown www-data:www-data /var/cache/snf-stats-app/",
            ]

    def _configure(self):
        r1 = {
            "STATS": self.ctx.stats.cname,
            "STATS_SECRET": config.stats_secret,
            }
        return [
            ("/etc/synnefo/stats.conf", r1, {}),
            ("/etc/collectd/synnefo-stats.conf", r1, {}),
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            "/etc/init.d/apache2 restart",
            ]


class GanetiCollectd(base.Component):
    def _configure(self):
        r1 = {
            "STATS": self.ctx.stats.cname,
            "COLLECTD_SECRET": config.collectd_secret,
            }
        return [
            ("/etc/collectd/passwd", {}, {}),
            ("/etc/collectd/synnefo-ganeti.conf", r1, {}),
            ]


class Archip(base.Component):
    REQUIRED_PACKAGES = [
        "librados2",
        "blktap-dkms",
        "blktap-archipelago-utils",
        "archipelago",
        "archipelago-dbg",
        "archipelago-rados",
        "archipelago-rados-dbg",
        "libxseg0",
        "libxseg0-dbg",
        "python-archipelago",
        "python-xseg",
        ]

    def required_components(self):
        return [Mount]

    @base.run_cmds
    def prepare(self):
        return ["mkdir -p /etc/archipelago"]

    def _configure(self):
        r1 = {
            "SEGMENT_SIZE": config.segment_size,
            "ARCHIP_DIR": config.archip_dir,
            }
        return [
            ("/etc/archipelago/archipelago.conf", r1, {})
            ]

    @base.run_cmds
    def restart(self):
        return [
            "archipelago restart"
            ]


class ArchipSynnefo(base.Component):
    REQUIRED_PACKAGES = []

    @base.run_cmds
    def prepare(self):
        return [
            "mkdir -p /etc/synnefo/gunicorn-hooks",
            "chown -R root:archipelago /etc/synnefo",
            "chown -R root:archipelago /var/log/gunicorn",
            "chmod g+s /etc/synnefo/",
            ]

    def _configure(self):
        r1 = {"HOST": self.node.fqdn}
        return [
            ("/etc/gunicorn.d/synnefo-archip", r1,
             {"remote": "/etc/gunicorn.d/synnefo"}),
            ("/etc/synnefo/gunicorn-hooks/gunicorn-archipelago.py", {}, {}),
            ]

    @base.run_cmds
    def restart(self):
        return [
            "/etc/init.d/gunicorn restart",
            ]


class ArchipGaneti(base.Component):
    REQUIRED_PACKAGES = [
        "archipelago-ganeti",
        ]


class ExtStorage(base.Component):
    @base.run_cmds
    def prepare(self):
        return ["mkdir -p /usr/local/lib/ganeti/"]

    @base.run_cmds
    def initialize(self):
        url = "http://code.grnet.gr/git/extstorage"
        extdir = "/usr/local/lib/ganeti/extstorage"
        return [
            "git clone %s %s" % (url, extdir)
            ]


class Client(base.Component):
    REQUIRED_PACKAGES = [
        "iceweasel"
        ]

    alias = constants.CLIENT

    def required_components(self):
        return [HW, SSH, DNS, APT, Kamaki, Burnin, Firefox]


class GanetiDev(base.Component):
    REQUIRED_PACKAGES = [
        "automake",
        "bridge-utils",
        "cabal-install",
        "fakeroot",
        "fping",
        "ghc",
        "ghc-haddock",
        "git",
        "graphviz",
        "hlint",
        "hscolour",
        "iproute",
        "iputils-arping",
        "libcurl4-openssl-dev",
        "libghc-attoparsec-dev",
        "libghc-crypto-dev",
        "libghc-curl-dev",
        "libghc-haddock-dev",
        "libghc-hinotify-dev",
        "libghc-hslogger-dev",
        "libghc-hunit-dev",
        "libghc-json-dev",
        "libghc-network-dev",
        "libghc-parallel-dev",
        "libghc-quickcheck2-dev",
        "libghc-regex-pcre-dev",
        "libghc-snap-server-dev",
        "libghc-temporary-dev",
        "libghc-test-framework-dev",
        "libghc-test-framework-hunit-dev",
        "libghc-test-framework-quickcheck2-dev",
        "libghc-base64-bytestring-dev",
        "libghc-text-dev",
        "libghc-utf8-string-dev",
        "libghc-vector-dev",
        "libghc-comonad-transformers-dev",
        "libpcre3-dev",
        "libghc6-zlib-dev",
        "libghc-lifted-base-dev",
        "libcurl4-openssl-dev",
        "shelltestrunner",
        "lvm2",
        "make",
        "ndisc6",
        "openssl",
        "pandoc",
        "pep8",
        "pylint",
        "python",
        "python-bitarray",
        "python-coverage",
        "python-epydoc",
        "python-ipaddr",
        "python-openssl",
        "python-pip",
        "python-pycurl",
        "python-pyinotify",
        "python-pyparsing",
        "python-setuptools",
        "python-simplejson",
        "python-sphinx",
        "python-yaml",
        "qemu-kvm",
        "socat",
        "ssh",
        "vim"
        ]

    CABAL = [
        "json",
        "network",
        "parallel",
        "utf8-string",
        "curl",
        "hslogger",
        "Crypto",
        "hinotify==0.3.2",
        "regex-pcre",
        "vector",
        "lifted-base==0.2.0.3",
        "lens==3.10",
        "base64-bytestring==1.0.0.1",
        ]

    def _cabal(self):
        ret = ["cabal update"]
        for p in self.CABAL:
            ret.append("cabal install %s" % p)
        return ret

    @base.run_cmds
    def prepare(self):
        src = config.src_dir
        url1 = "git://git.ganeti.org/ganeti.git"
        url2 = "https://code.grnet.gr/git/ganeti-local"
        return self._cabal() + [
            "git clone %s %s/ganeti" % (url1, src),
            "git clone %s %s/snf-ganeti" % (url2, src)
            ]

    def _configure(self):
        sample_nodes = []
        for node in self.ctx.cluster_nodes:
            n = config.get_info(node=node)
            sample_nodes.append({
                "primary": n.fqdn,
                "secondary": n.ip,
                })

        repl = {
            "CLUSTER_NAME": self.cluster.name,
            "VG": self.cluster.vg,
            "CLUSTER_NETDEV": self.cluster.netdev,
            "NODES": simplejson.dumps(sample_nodes),
            "DOMAIN": self.cluster.domain
            }
        c8 = os.path.join(config.src_dir, "ganeti", "configure-2.8")
        c10 = os.path.join(config.src_dir, "ganeti", "configure-2.10")
        return [
            ("/root/qa-sample.json", repl, {}),
            ("/tmp/configure-2.8", {}, {"remote": c8, "mode": 0755}),
            ("/tmp/configure-2.10", {}, {"remote": c10, "mode": 0755}),
            ]

    @base.run_cmds
    def initialize(self):
        d = os.path.join(config.src_dir, "ganeti")
        return [
            "cd %s; ./autogen.sh" % d,
            "cd %s; ./configure" % d,
            ]

    @base.run_cmds
    def test(self):
        ret = []
        for n in self.ctx.cluster_nodes:
            info = config.get_info(node=n)
            ret.append("ssh %s date" % info.name)
            ret.append("ssh %s date" % info.ip)
            ret.append("ssh %s date" % info.fqdn)
        return ret

    @update_admin
    @update_cluster_admin
    def admin_post(self):
        self.MASTER.add_qa_rapi_user()
        self.NS.add_qa_instances()


class Router(base.Component):
    REQUIRED_PACKAGES = [
        "iptables"
        ]


class Firefox(base.Component):
    REQUIRED_PACKAGES = [
        "iceweasel",
        ]

    @base.run_cmds
    def initialize(self):
        f = constants.CERT_OVERRIDE
        return [
            "cat /tmp/%s_* >> /etc/iceweasel/profile/%s" % (f, f)
            ]
