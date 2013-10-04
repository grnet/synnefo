# Too many lines in module pylint: disable-msg=C0302
# Too many arguments (7/5) pylint: disable-msg=R0913
"""
Fabric file for snf-deploy

"""

from __future__ import with_statement
from fabric.api import hide, env, settings, local, roles
from fabric.operations import run, put, get
import fabric
import re
import os
import shutil
import tempfile
import ast
from snfdeploy.lib import debug, Conf, Env, disable_color
from snfdeploy import massedit


def setup_env(confdir="conf", packages="packages", templates="files",
              cluster_name="ganeti1", autoconf=False, disable_colors=False,
              key_inject=False):
    """Setup environment"""
    print("Loading configuration for synnefo...")
    print(" * Using config files under %s..." % confdir)
    print(" * Using %s and %s for packages and templates accordingly..."
          % (packages, templates))

    autoconf = ast.literal_eval(autoconf)
    disable_colors = ast.literal_eval(disable_colors)
    env.key_inject = ast.literal_eval(key_inject)
    conf = Conf.configure(confdir=confdir, cluster_name=cluster_name,
                          autoconf=autoconf)
    env.env = Env(conf)

    env.local = autoconf
    env.password = env.env.password
    env.user = env.env.user
    env.shell = "/bin/bash -c"

    if disable_colors:
        disable_color()

    if env.env.cms.hostname in \
            [env.env.accounts.hostname, env.env.cyclades.hostname,
             env.env.pithos.hostname]:
        env.cms_pass = True
    else:
        env.cms_pass = False

    if env.env.accounts.hostname in \
            [env.env.cyclades.hostname, env.env.pithos.hostname]:
        env.csrf_disable = True
    else:
        env.csrf_disable = False

    env.roledefs = {
        "nodes": env.env.ips,
        "ips": env.env.ips,
        "accounts": [env.env.accounts.ip],
        "cyclades": [env.env.cyclades.ip],
        "pithos": [env.env.pithos.ip],
        "cms": [env.env.cms.ip],
        "mq": [env.env.mq.ip],
        "db": [env.env.db.ip],
        "mq": [env.env.mq.ip],
        "db": [env.env.db.ip],
        "ns": [env.env.ns.ip],
        "client": [env.env.client.ip],
        "router": [env.env.router.ip],
    }

    env.enable_lvm = False
    env.enable_drbd = False
    if ast.literal_eval(env.env.create_extra_disk) and env.env.extra_disk:
        env.enable_lvm = True
        env.enable_drbd = True

    env.roledefs.update({
        "ganeti": env.env.cluster_ips,
        "master": [env.env.master.ip],
    })


def install_package(package):
    debug(env.host, " * Installing package %s..." % package)
    apt_get = "export DEBIAN_FRONTEND=noninteractive ;" + \
              "apt-get install -y --force-yes "

    host_info = env.env.ips_info[env.host]
    env.env.update_packages(host_info.os)
    if ast.literal_eval(env.env.use_local_packages):
        with settings(warn_only=True):
            deb = local("ls %s/%s*%s_all.deb"
                        % (env.env.packages, package, host_info.os),
                        capture=True)
            if deb:
                debug(env.host,
                      " * Package %s found in %s..."
                      % (package, env.env.packages))
                try_put(deb, "/tmp/")
                try_run("dpkg -i /tmp/%s || "
                        % os.path.basename(deb) + apt_get + "-f")
                try_run("rm /tmp/%s" % os.path.basename(deb))
                return

    info = getattr(env.env, package)
    if info in \
            ["squeeze-backports", "squeeze", "stable",
             "testing", "unstable", "wheezy"]:
        apt_get += " -t %s %s " % (info, package)
    elif info:
        apt_get += " %s=%s " % (package, info)
    else:
        apt_get += package

    try_run(apt_get)

    return


@roles("ns")
def update_ns_for_ganeti():
    debug(env.host,
          "Updating name server entries for backend %s..."
          % env.env.cluster.fqdn)
    update_arecord(env.env.cluster)
    update_ptrrecord(env.env.cluster)
    try_run("/etc/init.d/bind9 restart")


@roles("ns")
def update_ns_for_node(node):
    info = env.env.nodes_info.get(node)
    update_arecord(info)
    update_ptrrecord(info)
    try_run("/etc/init.d/bind9 restart")


@roles("ns")
def update_arecord(host):
    filename = "/etc/bind/zones/" + env.env.domain
    cmd = """
    echo '{0}' >> {1}
    """.format(host.arecord, filename)
    try_run(cmd)


@roles("ns")
def update_cnamerecord(host):
    filename = "/etc/bind/zones/" + env.env.domain
    cmd = """
    echo '{0}' >> {1}
    """.format(host.cnamerecord, filename)
    try_run(cmd)


@roles("ns")
def update_ptrrecord(host):
    filename = "/etc/bind/rev/synnefo.in-addr.arpa.zone"
    cmd = """
    echo '{0}' >> {1}
    """.format(host.ptrrecord, filename)
    try_run(cmd)


@roles("nodes")
def apt_get_update():
    debug(env.host, "apt-get update....")
    try_run("apt-get update")


@roles("ns")
def setup_ns():
    debug(env.host, "Setting up name server..")
    #WARNING: this should be remove after we are done
    # because gevent does pick randomly nameservers and google does
    # not know our setup!!!!!
    apt_get_update()
    install_package("bind9")
    tmpl = "/etc/bind/named.conf.local"
    replace = {
        "domain": env.env.domain,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)

    try_run("mkdir -p /etc/bind/zones")
    tmpl = "/etc/bind/zones/example.com"
    replace = {
        "domain": env.env.domain,
        "ns_node_ip": env.env.ns.ip,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    remote = "/etc/bind/zones/" + env.env.domain
    try_put(custom, remote)

    try_run("mkdir -p /etc/bind/rev")
    tmpl = "/etc/bind/rev/synnefo.in-addr.arpa.zone"
    replace = {
        "domain": env.env.domain,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)

    tmpl = "/etc/bind/named.conf.options"
    replace = {
        "NODE_IPS": ";".join(env.env.ips),
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)

    for role, info in env.env.roles.iteritems():
        if role == "ns":
            continue
        update_cnamerecord(info)
    for node, info in env.env.nodes_info.iteritems():
        update_arecord(info)
        update_ptrrecord(info)

    try_run("/etc/init.d/bind9 restart")


@roles("nodes")
def check_dhcp():
    debug(env.host, "Checking IPs for synnefo..")
    for n, info in env.env.nodes_info.iteritems():
        try_run("ping -c 1 " + info.ip)


@roles("nodes")
def check_dns():
    debug(env.host, "Checking fqdns for synnefo..")
    for n, info in env.env.nodes_info.iteritems():
        try_run("ping -c 1 " + info.fqdn)

    for n, info in env.env.roles.iteritems():
        try_run("ping -c 1 " + info.fqdn)


@roles("nodes")
def check_connectivity():
    debug(env.host, "Checking internet connectivity..")
    try_run("ping -c 1 www.google.com")


@roles("nodes")
def check_ssh():
    debug(env.host, "Checking password-less ssh..")
    for n, info in env.env.nodes_info.iteritems():
        try_run("ssh " + info.fqdn + "  date")


@roles("ips")
def add_keys():
    if not env.key_inject:
        debug(env.host, "Skipping ssh keys injection..")
        return
    else:
        debug(env.host, "Adding rsa/dsa keys..")
    try_run("mkdir -p /root/.ssh")
    cmd = """
for f in $(ls /root/.ssh/*); do
  cp $f $f.bak
done
    """
    try_run(cmd)
    files = ["authorized_keys", "id_dsa", "id_dsa.pub",
             "id_rsa", "id_rsa.pub"]
    for f in files:
        tmpl = "/root/.ssh/" + f
        replace = {}
        custom = customize_settings_from_tmpl(tmpl, replace)
        try_put(custom, tmpl, mode=0600)

    cmd = """
if [ -e /root/.ssh/authorized_keys.bak ]; then
  cat /root/.ssh/authorized_keys.bak >> /root/.ssh/authorized_keys
fi
    """
    debug(env.host, "Updating exising authorized keys..")
    try_run(cmd)


@roles("ips")
def setup_resolv_conf():
    debug(env.host, "Tweak /etc/resolv.conf...")
    try_run("/etc/init.d/network-manager stop", abort=False)
    tmpl = "/etc/dhcp/dhclient-enter-hooks.d/nodnsupdate"
    replace = {}
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    try_run("cp /etc/resolv.conf /etc/resolv.conf.bak")
    tmpl = "/etc/resolv.conf"
    replace = {
        "domain": env.env.domain,
        "ns_node_ip": env.env.ns.ip,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try:
        try_put(custom, tmpl)
        cmd = """
        echo "\
# This has been generated automatically by snf-deploy, at
# $(date).
# The immutable bit (+i attribute) has been used to avoid it being
# overwritten by software such as NetworkManager or resolvconf.
# Use lsattr/chattr to view or modify its file attributes.


$(cat {0})" > {0}
""".format(tmpl)
        try_run(cmd)
    except:
        pass
    try_run("chattr +i /etc/resolv.conf")


@roles("ips")
def setup_hosts():
    debug(env.host, "Tweaking /etc/hosts and ssh_config files...")
    try_run("echo StrictHostKeyChecking no >> /etc/ssh/ssh_config")
    cmd = "sed -i 's/^127.*$/127.0.0.1 localhost/g' /etc/hosts "
    try_run(cmd)
    host_info = env.env.ips_info[env.host]
    cmd = "hostname %s" % host_info.hostname
    try_run(cmd)
    cmd = "echo %s > /etc/hostname" % host_info.hostname
    try_run(cmd)


def try_run(cmd, abort=True):
    try:
        if env.local:
            return local(cmd, capture=True)
        else:
            return run(cmd)
    except BaseException as e:
        if abort:
            fabric.utils.abort(e)
        else:
            debug(env.host, "WARNING: command failed. Continuing anyway...")


def try_put(local_path=None, remote_path=None, abort=True, **kwargs):
    try:
        put(local_path=local_path, remote_path=remote_path, **kwargs)
    except BaseException as e:
        if abort:
            fabric.utils.abort(e)
        else:
            debug(env.host, "WARNING: command failed. Continuing anyway...")


def try_get(remote_path, local_path=None, abort=True, **kwargs):
    try:
        get(remote_path, local_path=local_path, **kwargs)
    except BaseException as e:
        if abort:
            fabric.utils.abort(e)
        else:
            debug(env.host, "WARNING: command failed. Continuing anyway...")


def create_bridges():
    debug(env.host, " * Creating bridges...")
    install_package("bridge-utils")
    cmd = """
    brctl addbr {0} ; ip link set {0} up
    """.format(env.env.common_bridge)
    try_run(cmd)


def connect_bridges():
    debug(env.host, " * Connecting bridges...")
    #cmd = """
    #brctl addif {0} {1}
    #""".format(env.env.common_bridge, env.env.public_iface)
    #try_run(cmd)


@roles("ganeti")
def setup_net_infra():
    debug(env.host, "Setup networking infrastracture..")
    create_bridges()
    connect_bridges()


@roles("ganeti")
def setup_lvm():
    debug(env.host, "create volume group %s for ganeti.." % env.env.vg)
    if env.enable_lvm:
        install_package("lvm2")
        cmd = """
        pvcreate {0}
        vgcreate {1} {0}
        """.format(env.env.extra_disk, env.env.vg)
        try_run(cmd)


def customize_settings_from_tmpl(tmpl, replace):
    debug(env.host, " * Customizing template %s..." % tmpl)
    local = env.env.templates + tmpl
    _, custom = tempfile.mkstemp()
    shutil.copyfile(local, custom)
    for k, v in replace.iteritems():
        regex = "re.sub('%{0}%', '{1}', line)".format(k.upper(), v)
        massedit.edit_files([custom], [regex], dry_run=False)

    return custom


@roles("nodes")
def setup_apt():
    debug(env.host, "Setting up apt sources...")
    install_package("curl")
    cmd = """
    echo 'APT::Install-Suggests "false";' >> /etc/apt/apt.conf
    curl -k https://dev.grnet.gr/files/apt-grnetdev.pub | apt-key add -
    """
    try_run(cmd)
    host_info = env.env.ips_info[env.host]
    if host_info.os == "squeeze":
        tmpl = "/etc/apt/sources.list.d/synnefo.squeeze.list"
    else:
        tmpl = "/etc/apt/sources.list.d/synnefo.wheezy.list"
    replace = {}
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)
    apt_get_update()


@roles("cyclades", "cms", "pithos", "accounts")
def restart_services():
    debug(env.host, " * Restarting apache2 and gunicorn...")
    try_run("/etc/init.d/gunicorn restart")
    try_run("/etc/init.d/apache2 restart")


def setup_gunicorn():
    debug(env.host, " * Setting up gunicorn...")
    install_package("gunicorn")
    tmpl = "/etc/gunicorn.d/synnefo"
    replace = {}
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    try_run("/etc/init.d/gunicorn restart")


def setup_apache():
    debug(env.host, " * Setting up apache2...")
    host_info = env.env.ips_info[env.host]
    install_package("apache2")
    tmpl = "/etc/apache2/sites-available/synnefo"
    replace = {
        "HOST": host_info.fqdn,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)
    tmpl = "/etc/apache2/sites-available/synnefo-ssl"
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)
    cmd = """
    a2enmod ssl
    a2enmod rewrite
    a2dissite default
    a2ensite synnefo
    a2ensite synnefo-ssl
    a2enmod headers
    a2enmod proxy_http
    a2dismod autoindex
    """
    try_run(cmd)
    try_run("/etc/init.d/apache2 restart")


@roles("mq")
def setup_mq():
    debug(env.host, "Setting up RabbitMQ...")
    install_package("rabbitmq-server")
    cmd = """
    rabbitmqctl add_user {0} {1}
    rabbitmqctl set_permissions {0} ".*" ".*" ".*"
    rabbitmqctl delete_user guest
    rabbitmqctl set_user_tags {0} administrator
    """.format(env.env.synnefo_user, env.env.synnefo_rabbitmq_passwd)
    try_run(cmd)
    try_run("/etc/init.d/rabbitmq-server restart")


@roles("db")
def allow_access_in_db(ip, user="all", method="md5"):
    cmd = """
    pg_hba=$(ls /etc/postgresql/*/main/pg_hba.conf)
    echo host all {0} {1}/32 {2} >> $pg_hba
    """.format(user, ip, method)
    try_run(cmd)
    cmd = """
    pg_hba=$(ls /etc/postgresql/*/main/pg_hba.conf)
    sed -i 's/\(host.*127.0.0.1.*\)md5/\\1trust/' $pg_hba
    """
    try_run(cmd)
    try_run("/etc/init.d/postgresql restart")


@roles("db")
def setup_db():
    debug(env.host, "Setting up DataBase server...")
    install_package("postgresql")

    tmpl = "/tmp/db-init.psql"
    replace = {
        "synnefo_user": env.env.synnefo_user,
        "synnefo_db_passwd": env.env.synnefo_db_passwd,
        }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)
    cmd = 'su - postgres -c "psql -w -f %s" ' % tmpl
    try_run(cmd)
    cmd = """
    conf=$(ls /etc/postgresql/*/main/postgresql.conf)
    echo "listen_addresses = '*'" >> $conf
    """
    try_run(cmd)

    if env.env.testing_vm:
        cmd = """
        conf=$(ls /etc/postgresql/*/main/postgresql.conf)
        echo "fsync=off\nsynchronous_commit=off\nfull_page_writes=off" >> $conf
        """
        try_run(cmd)

    allow_access_in_db(env.host, "all", "trust")
    try_run("/etc/init.d/postgresql restart")


@roles("db")
def destroy_db():
    try_run("""su - postgres -c ' psql -w -c "drop database snf_apps" '""")
    try_run("""su - postgres -c ' psql -w -c "drop database snf_pithos" '""")


def setup_webproject():
    debug(env.host, " * Setting up snf-webproject...")
    with settings(hide("everything")):
        try_run("ping -c1 " + env.env.db.ip)
    setup_common()
    install_package("snf-webproject")
    install_package("python-psycopg2")
    install_package("python-gevent")
    install_package("python-django")
    tmpl = "/etc/synnefo/webproject.conf"
    replace = {
        "synnefo_user": env.env.synnefo_user,
        "synnefo_db_passwd": env.env.synnefo_db_passwd,
        "db_node": env.env.db.ip,
        "domain": env.env.domain,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    with settings(host_string=env.env.db.ip):
        host_info = env.env.ips_info[env.host]
        allow_access_in_db(host_info.ip, "all", "trust")
    try_run("/etc/init.d/gunicorn restart")


def setup_common():
    debug(env.host, " * Setting up snf-common...")
    host_info = env.env.ips_info[env.host]
    install_package("python-objpool")
    install_package("snf-common")
    install_package("python-astakosclient")
    install_package("snf-django-lib")
    install_package("snf-branding")
    tmpl = "/etc/synnefo/common.conf"
    replace = {
        #FIXME:
        "EMAIL_SUBJECT_PREFIX": env.host,
        "domain": env.env.domain,
        "HOST": host_info.fqdn,
        "MAIL_DIR": env.env.mail_dir,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    try_run("mkdir -p {0}; chmod 777 {0}".format(env.env.mail_dir))
    try_run("/etc/init.d/gunicorn restart")


@roles("accounts")
def astakos_loaddata():
    debug(env.host, " * Loading initial data to astakos...")
    cmd = """
    snf-manage loaddata groups
    """
    try_run(cmd)


@roles("accounts")
def astakos_register_components():
    debug(env.host, " * Register services in astakos...")

    cyclades_base_url = "https://%s/cyclades" % env.env.cyclades.fqdn
    pithos_base_url = "https://%s/pithos" % env.env.pithos.fqdn
    astakos_base_url = "https://%s/astakos" % env.env.accounts.fqdn

    cmd = """
    snf-manage component-add "home" --ui-url https://{0}
    snf-manage component-add "cyclades" --base-url {1} --ui-url {1}/ui
    snf-manage component-add "pithos" --base-url {2} --ui-url {2}/ui
    snf-manage component-add "astakos" --base-url {3} --ui-url {3}/ui
    """.format(env.env.cms.fqdn, cyclades_base_url,
               pithos_base_url, astakos_base_url)
    try_run(cmd)


@roles("accounts")
def add_user():
    debug(env.host, " * adding user %s to astakos..." % env.env.user_email)
    email = env.env.user_email
    name = env.env.user_name
    lastname = env.env.user_lastname
    passwd = env.env.user_passwd
    cmd = """
    snf-manage user-add {0} {1} {2}
    """.format(email, name, lastname)
    try_run(cmd)
    with settings(host_string=env.env.db.ip):
        uid, user_auth_token, user_uuid = get_auth_token_from_db(email)
    cmd = """
    snf-manage user-modify --password {0} {1}
    """.format(passwd, uid)
    try_run(cmd)


@roles("accounts")
def activate_user(user_email=None):
    if not user_email:
        user_email = env.env.user_email
    debug(env.host, " * Activate user %s..." % user_email)
    with settings(host_string=env.env.db.ip):
        uid, user_auth_token, user_uuid = get_auth_token_from_db(user_email)

    cmd = """
    snf-manage user-modify --verify {0}
    snf-manage user-modify --accept {0}
    """.format(uid)
    try_run(cmd)


@roles("accounts")
def setup_astakos():
    debug(env.host, "Setting up snf-astakos-app...")
    setup_gunicorn()
    setup_apache()
    setup_webproject()
    install_package("python-django-south")
    install_package("snf-astakos-app")
    install_package("kamaki")

    tmpl = "/etc/synnefo/astakos.conf"
    replace = {
        "ACCOUNTS": env.env.accounts.fqdn,
        "domain": env.env.domain,
        "CYCLADES": env.env.cyclades.fqdn,
        "PITHOS": env.env.pithos.fqdn,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    if env.csrf_disable:
        cmd = """
cat <<EOF >> /etc/synnefo/astakos.conf
try:
  MIDDLEWARE_CLASSES.remove('django.middleware.csrf.CsrfViewMiddleware')
except:
  pass
EOF
"""
        try_run(cmd)

    try_run("/etc/init.d/gunicorn restart")

    cmd = """
    snf-manage syncdb --noinput
    snf-manage migrate im --delete-ghost-migrations
    snf-manage migrate quotaholder_app
    """
    try_run(cmd)


@roles("accounts")
def get_service_details(service="pithos"):
    debug(env.host,
          " * Getting registered details for %s service..." % service)
    result = try_run("snf-manage component-list -o id,name,token")
    r = re.compile(r".*%s.*" % service, re.M)
    service_id, _, service_token = r.search(result).group().split()
    # print("%s: %s %s" % (service, service_id, service_token))
    return (service_id, service_token)


@roles("db")
def get_auth_token_from_db(user_email=None):
    if not user_email:
        user_email = env.env.user_email
    debug(env.host,
          " * Getting authentication token and uuid for user %s..."
          % user_email)
    cmd = """
echo "select id, auth_token, uuid, email from auth_user, im_astakosuser \
where auth_user.id = im_astakosuser.user_ptr_id and auth_user.email = '{0}';" \
> /tmp/psqlcmd
su - postgres -c  "psql -w -d snf_apps -f /tmp/psqlcmd"
""".format(user_email)

    result = try_run(cmd)
    r = re.compile(r"(\d+)[ |]*(\S+)[ |]*(\S+)[ |]*" + user_email, re.M)
    match = r.search(result)
    uid, user_auth_token, user_uuid = match.groups()
    # print("%s: %s %s %s" % ( user_email, uid, user_auth_token, user_uuid))

    return (uid, user_auth_token, user_uuid)


@roles("cms")
def cms_loaddata():
    debug(env.host, " * Loading cms initial data...")
    if env.cms_pass:
        debug(env.host, "Aborting. Prerequisites not met.")
        return
    tmpl = "/tmp/sites.json"
    replace = {}
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)

    tmpl = "/tmp/page.json"
    replace = {}
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)

    cmd = """
    snf-manage loaddata /tmp/sites.json
    snf-manage loaddata /tmp/page.json
    snf-manage createsuperuser --username=admin --email=admin@{0} --noinput
    """.format(env.env.domain)
    try_run(cmd)


@roles("cms")
def setup_cms():
    debug(env.host, "Setting up cms...")
    if env.cms_pass:
        debug(env.host, "Aborting. Prerequisites not met.")
        return
    with settings(hide("everything")):
        try_run("ping -c1 accounts." + env.env.domain)
    setup_gunicorn()
    setup_apache()
    setup_webproject()
    install_package("snf-cloudcms")

    tmpl = "/etc/synnefo/cms.conf"
    replace = {
        "ACCOUNTS": env.env.accounts.fqdn,
        }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    try_run("/etc/init.d/gunicorn restart")

    cmd = """
    snf-manage syncdb
    snf-manage migrate --delete-ghost-migrations
    """.format(env.env.domain)
    try_run(cmd)


def setup_nfs_dirs():
    debug(env.host, " * Creating NFS mount point for pithos and ganeti...")
    cmd = """
    mkdir -p {0}
    cd {0}
    mkdir -p data
    chown www-data:www-data data
    chmod g+ws data
    mkdir -p /srv/okeanos
    """.format(env.env.pithos_dir)
    try_run(cmd)


@roles("nodes")
def setup_nfs_clients():
    if env.host == env.env.pithos.ip:
        return

    host_info = env.env.ips_info[env.host]
    debug(env.host, " * Mounting pithos NFS mount point...")
    with settings(hide("everything")):
        try_run("ping -c1 " + env.env.pithos.hostname)
    with settings(host_string=env.env.pithos.ip):
        update_nfs_exports(host_info.ip)

    install_package("nfs-common")
    for d in [env.env.pithos_dir, env.env.image_dir]:
        try_run("mkdir -p " + d)
        cmd = """
echo "{0}:{1} {1}  nfs defaults,rw,noatime,rsize=131072,\
wsize=131072,timeo=14,intr,noacl" >> /etc/fstab
""".format(env.env.pithos.ip, d)
        try_run(cmd)
        try_run("mount " + d)


@roles("pithos")
def update_nfs_exports(ip):
    tmpl = "/tmp/exports"
    replace = {
        "pithos_dir": env.env.pithos_dir,
        "image_dir": env.env.image_dir,
        "ip": ip,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)
    try_run("cat %s >> /etc/exports" % tmpl)
    try_run("/etc/init.d/nfs-kernel-server restart")


@roles("pithos")
def setup_nfs_server():
    debug(env.host, " * Setting up NFS server for pithos...")
    setup_nfs_dirs()
    install_package("nfs-kernel-server")


@roles("pithos")
def setup_pithos():
    debug(env.host, "Setting up snf-pithos-app...")
    with settings(hide("everything")):
        try_run("ping -c1 accounts." + env.env.domain)
        try_run("ping -c1 " + env.env.db.ip)
    setup_gunicorn()
    setup_apache()
    setup_webproject()

    with settings(host_string=env.env.accounts.ip):
        service_id, service_token = get_service_details("pithos")

    install_package("kamaki")
    install_package("snf-pithos-backend")
    install_package("snf-pithos-app")
    tmpl = "/etc/synnefo/pithos.conf"
    replace = {
        "ACCOUNTS": env.env.accounts.fqdn,
        "PITHOS": env.env.pithos.fqdn,
        "db_node": env.env.db.ip,
        "synnefo_user": env.env.synnefo_user,
        "synnefo_db_passwd": env.env.synnefo_db_passwd,
        "pithos_dir": env.env.pithos_dir,
        "PITHOS_SERVICE_TOKEN": service_token,
        "proxy": env.env.pithos.hostname == env.env.accounts.hostname
        }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    try_run("/etc/init.d/gunicorn restart")

    install_package("snf-pithos-webclient")
    tmpl = "/etc/synnefo/webclient.conf"
    replace = {
        "ACCOUNTS": env.env.accounts.fqdn,
        "PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE": service_id,
        }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)

    try_run("/etc/init.d/gunicorn restart")
    #TOFIX: the previous command lets pithos-backend create blocks and maps
    #       with root owner
    try_run("chown -R www-data:www-data %s/data " % env.env.pithos_dir)
    #try_run("pithos-migrate stamp 4c8ccdc58192")
    #try_run("pithos-migrate upgrade head")


@roles("ganeti")
def setup_ganeti():
    debug(env.host, "Setting up snf-ganeti...")
    node_info = env.env.ips_info[env.host]
    with settings(hide("everything")):
        #if env.enable_lvm:
        #    try_run("vgs " + env.env.vg)
        try_run("getent hosts " + env.env.cluster.fqdn)
        try_run("getent hosts %s | grep -v ^127" % env.host)
        try_run("hostname -f | grep " + node_info.fqdn)
        #try_run("ip link show " + env.env.common_bridge)
        #try_run("ip link show " + env.env.common_bridge)
        #try_run("apt-get update")
    install_package("qemu-kvm")
    install_package("python-bitarray")
    install_package("ganeti-htools")
    install_package("snf-ganeti")
    try_run("mkdir -p /srv/ganeti/file-storage/")
    cmd = """
cat <<EOF > /etc/ganeti/file-storage-paths
/srv/ganeti/file-storage
/srv/ganeti/shared-file-storage
EOF
"""
    try_run(cmd)


@roles("master")
def add_rapi_user():
    debug(env.host, " * Adding RAPI user to Ganeti backend...")
    cmd = """
    echo -n "{0}:Ganeti Remote API:{1}" | openssl md5
    """.format(env.env.synnefo_user, env.env.synnefo_rapi_passwd)
    result = try_run(cmd)
    if result.startswith("(stdin)= "):
        result = result.split("(stdin)= ")[1]
    cmd = """
    echo "{0} {1}{2} write" >> /var/lib/ganeti/rapi/users
    """.format(env.env.synnefo_user, '{ha1}', result)
    try_run(cmd)
    try_run("/etc/init.d/ganeti restart")


@roles("master")
def add_nodes():
    nodes = env.env.cluster_nodes.split(",")
    nodes.remove(env.env.master_node)
    debug(env.host, " * Adding nodes to Ganeti backend...")
    for n in nodes:
        add_node(n)


@roles("master")
def add_node(node):
    node_info = env.env.nodes_info[node]
    debug(env.host, " * Adding node %s to Ganeti backend..." % node_info.fqdn)
    cmd = "gnt-node add --no-ssh-key-check --master-capable=yes " + \
          "--vm-capable=yes " + node_info.fqdn
    try_run(cmd)


@roles("ganeti")
def enable_drbd():
    if env.enable_drbd:
        debug(env.host, " * Enabling DRBD...")
        try_run("modprobe drbd minor_count=255 usermode_helper=/bin/true")
        try_run("echo drbd minor_count=255 usermode_helper=/bin/true " +
                ">> /etc/modules")


@roles("master")
def setup_drbd_dparams():
    if env.enable_drbd:
        debug(env.host,
              " * Twicking drbd related disk parameters in Ganeti...")
        cmd = """
        gnt-cluster modify --disk-parameters=drbd:metavg={0}
        gnt-group modify --disk-parameters=drbd:metavg={0} default
        """.format(env.env.vg)
        try_run(cmd)


@roles("master")
def enable_lvm():
    if env.enable_lvm:
        debug(env.host, " * Enabling LVM...")
        cmd = """
        gnt-cluster modify --vg-name={0}
        """.format(env.env.vg)
        try_run(cmd)
    else:
        debug(env.host, " * Disabling LVM...")
        try_run("gnt-cluster modify --no-lvm-storage")


@roles("master")
def destroy_cluster():
    debug(env.host, " * Destroying Ganeti cluster...")
    #TODO: remove instances first
    allnodes = env.env.cluster_hostnames[:]
    allnodes.remove(env.host)
    for n in allnodes:
        host_info = env.env.ips_info[env.host]
        debug(env.host, " * Removing node %s..." % n)
        cmd = "gnt-node remove  " + host_info.fqdn
        try_run(cmd)
    try_run("gnt-cluster destroy --yes-do-it")


@roles("master")
def init_cluster():
    debug(env.host, " * Initializing Ganeti backend...")
    # extra = ""
    # if env.enable_lvm:
    #     extra += " --vg-name={0} ".format(env.env.vg)
    # else:
    #     extra += " --no-lvm-storage "
    # if not env.enable_drbd:
    #     extra += " --no-drbd-storage "
    extra = " --no-lvm-storage --no-drbd-storage "
    cmd = """
    gnt-cluster init --enabled-hypervisors=kvm \
        {0} \
        --nic-parameters link={1},mode=bridged \
        --master-netdev {2} \
        --default-iallocator hail \
        --hypervisor-parameters kvm:kernel_path=,vnc_bind_address=0.0.0.0 \
        --no-ssh-init --no-etc-hosts \
        {3}
    """.format(extra, env.env.common_bridge,
               env.env.cluster_netdev, env.env.cluster.fqdn)
    try_run(cmd)


@roles("ganeti")
def debootstrap():
    install_package("ganeti-instance-debootstrap")


@roles("ganeti")
def setup_image_host():
    debug(env.host, "Setting up snf-image...")
    install_package("snf-pithos-backend")
    install_package("snf-image")
    try_run("mkdir -p %s" % env.env.image_dir)
    tmpl = "/etc/default/snf-image"
    replace = {
        "synnefo_user": env.env.synnefo_user,
        "synnefo_db_passwd": env.env.synnefo_db_passwd,
        "pithos_dir": env.env.pithos_dir,
        "db_node": env.env.db.ip,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)


@roles("ganeti")
def setup_image_helper():
    debug(env.host, " * Updating helper image...")
    cmd = """
    snf-image-update-helper -y
    """
    try_run(cmd)


@roles("ganeti")
def setup_gtools():
    debug(env.host, " * Setting up snf-cyclades-gtools...")
    with settings(hide("everything")):
        try_run("ping -c1 " + env.env.mq.ip)
    setup_common()
    install_package("snf-cyclades-gtools")
    tmpl = "/etc/synnefo/gtools.conf"
    replace = {
        "synnefo_user": env.env.synnefo_user,
        "synnefo_rabbitmq_passwd": env.env.synnefo_rabbitmq_passwd,
        "mq_node": env.env.mq.ip,
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)

    cmd = """
    sed -i 's/false/true/' /etc/default/snf-ganeti-eventd
    /etc/init.d/snf-ganeti-eventd start
    """
    try_run(cmd)


@roles("ganeti")
def setup_iptables():
    debug(env.host, " * Setting up iptables to mangle DHCP requests...")
    cmd = """
    iptables -t mangle -A PREROUTING -i br+ -p udp -m udp --dport 67 \
            -j NFQUEUE --queue-num 42
    iptables -t mangle -A PREROUTING -i tap+ -p udp -m udp --dport 67 \
            -j NFQUEUE --queue-num 42
    iptables -t mangle -A PREROUTING -i prv+ -p udp -m udp --dport 67 \
            -j NFQUEUE --queue-num 42

    ip6tables -t mangle -A PREROUTING -i br+ -p ipv6-icmp -m icmp6 \
            --icmpv6-type 133 -j NFQUEUE --queue-num 43
    ip6tables -t mangle -A PREROUTING -i br+ -p ipv6-icmp -m icmp6 \
            --icmpv6-type 135 -j NFQUEUE --queue-num 44
    """
    try_run(cmd)


@roles("ganeti")
def setup_network():
    debug(env.host,
          "Setting up networking for Ganeti instances (nfdhcpd, etc.)...")
    install_package("nfqueue-bindings-python")
    install_package("nfdhcpd")
    tmpl = "/etc/nfdhcpd/nfdhcpd.conf"
    replace = {
        "ns_node_ip": env.env.ns.ip
    }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl)
    try_run("/etc/init.d/nfdhcpd restart")

    install_package("snf-network")
    cmd = """
sed -i 's/MAC_MASK.*/MAC_MASK = ff:ff:f0:00:00:00/' /etc/default/snf-network
    """
    try_run(cmd)


@roles("router")
def setup_router():
    debug(env.host, " * Setting up internal router for NAT...")
    cmd = """
    echo 1 > /proc/sys/net/ipv4/ip_forward
    iptables -t nat -A POSTROUTING -s {0} -o {3} -j MASQUERADE
    ip addr add {1} dev {2}
    ip route add {0} dev {2} src {1}
    """.format(env.env.synnefo_public_network_subnet,
               env.env.synnefo_public_network_gateway,
               env.env.common_bridge, env.env.public_iface)
    try_run(cmd)


@roles("cyclades")
def cyclades_loaddata():
    debug(env.host, " * Loading initial data for cyclades...")
    try_run("snf-manage flavor-create %s %s %s %s" % (env.env.flavor_cpu,
                                                      env.env.flavor_ram,
                                                      env.env.flavor_disk,
                                                      env.env.flavor_storage))
    #run("snf-manage loaddata flavors")


@roles("cyclades")
def setup_cyclades():
    debug(env.host, "Setting up snf-cyclades-app...")
    with settings(hide("everything")):
        try_run("ping -c1 accounts." + env.env.domain)
        try_run("ping -c1 " + env.env.db.ip)
        try_run("ping -c1 " + env.env.mq.ip)
    setup_gunicorn()
    setup_apache()
    setup_webproject()
    install_package("memcached")
    install_package("python-memcache")
    install_package("snf-pithos-backend")
    install_package("kamaki")
    install_package("snf-cyclades-app")
    install_package("python-django-south")
    tmpl = "/etc/synnefo/cyclades.conf"

    with settings(host_string=env.env.accounts.ip):
        service_id, service_token = get_service_details("cyclades")

    replace = {
        "ACCOUNTS": env.env.accounts.fqdn,
        "CYCLADES": env.env.cyclades.fqdn,
        "mq_node": env.env.mq.ip,
        "db_node": env.env.db.ip,
        "synnefo_user": env.env.synnefo_user,
        "synnefo_db_passwd": env.env.synnefo_db_passwd,
        "synnefo_rabbitmq_passwd": env.env.synnefo_rabbitmq_passwd,
        "pithos_dir": env.env.pithos_dir,
        "common_bridge": env.env.common_bridge,
        "HOST": env.env.cyclades.ip,
        "domain": env.env.domain,
        "CYCLADES_SERVICE_TOKEN": service_token,
        "proxy": env.env.cyclades.hostname == env.env.accounts.hostname
        }
    custom = customize_settings_from_tmpl(tmpl, replace)
    try_put(custom, tmpl, mode=0644)
    try_run("/etc/init.d/gunicorn restart")

    cmd = """
    sed -i 's/false/true/' /etc/default/snf-dispatcher
    /etc/init.d/snf-dispatcher start
    """
    try_run(cmd)

    try_run("snf-manage syncdb")
    try_run("snf-manage migrate --delete-ghost-migrations")


@roles("cyclades")
def get_backend_id(cluster_name="ganeti1.synnefo.deploy.local"):
    backend_id = try_run("snf-manage backend-list 2>/dev/null " +
                         "| grep %s | awk '{print $1}'" % cluster_name)
    return backend_id


@roles("cyclades")
def add_backend():
    debug(env.host,
          "adding %s ganeti backend to cyclades..." % env.env.cluster.fqdn)
    with settings(hide("everything")):
        try_run("ping -c1 " + env.env.cluster.fqdn)
    cmd = """
    snf-manage backend-add --clustername={0} --user={1} --pass={2}
    """.format(env.env.cluster.fqdn, env.env.synnefo_user,
               env.env.synnefo_rapi_passwd)
    try_run(cmd)
    backend_id = get_backend_id(env.env.cluster.fqdn)
    try_run("snf-manage backend-modify --drained=False " + backend_id)


@roles("cyclades")
def pin_user_to_backend(user_email):
    backend_id = get_backend_id(env.env.cluster.fqdn)
    # pin user to backend
    cmd = """
cat <<EOF >> /etc/synnefo/cyclades.conf

BACKEND_PER_USER = {
  '{0}': {1},
}

EOF
/etc/init.d/gunicorn restart
""".format(user_email, backend_id)
    try_run(cmd)


@roles("cyclades")
def add_pools():
    debug(env.host,
          " * Creating pools of resources (brigdes, mac prefixes) " +
          "in cyclades...")
    try_run("snf-manage pool-create --type=mac-prefix " +
            "--base=aa:00:0 --size=65536")
    try_run("snf-manage pool-create --type=bridge --base=prv --size=20")


@roles("accounts", "cyclades", "pithos")
def export_services():
    debug(env.host, " * Exporting services...")
    host = env.host
    services = []
    if host == env.env.cyclades.ip:
        services.append("cyclades")
    if host == env.env.pithos.ip:
        services.append("pithos")
    if host == env.env.accounts.ip:
        services.append("astakos")
    for service in services:
        filename = "%s_services.json" % service
        cmd = "snf-manage service-export-%s > %s" % (service, filename)
        run(cmd)
        try_get(filename, filename+".local")


@roles("accounts")
def import_services():
    debug(env.host, " * Registering services to astakos...")
    for service in ["cyclades", "pithos", "astakos"]:
        filename = "%s_services.json" % service
        try_put(filename + ".local", filename)
        cmd = "snf-manage service-import --json=%s" % filename
        run(cmd)

    debug(env.host, " * Setting default quota...")
    cmd = """
    snf-manage resource-modify --limit 40G pithos.diskspace
    snf-manage resource-modify --limit 2 astakos.pending_app
    snf-manage resource-modify --limit 4 cyclades.vm
    snf-manage resource-modify --limit 40G cyclades.disk
    snf-manage resource-modify --limit 16G cyclades.ram
    snf-manage resource-modify --limit 8G cyclades.active_ram
    snf-manage resource-modify --limit 32 cyclades.cpu
    snf-manage resource-modify --limit 16 cyclades.active_cpu
    snf-manage resource-modify --limit 4 cyclades.network.private
    """
    try_run(cmd)


@roles("cyclades")
def add_network():
    debug(env.host, " * Adding public network in cyclades...")
    backend_id = get_backend_id(env.env.cluster.fqdn)
    cmd = """
    snf-manage network-create --subnet={0} --gateway={1} --public \
        --dhcp=True --flavor={2} --mode=bridged --link={3} --name=Internet \
        --backend-id={4} --floating-ip-pool=True
    """.format(env.env.synnefo_public_network_subnet,
               env.env.synnefo_public_network_gateway,
               env.env.synnefo_public_network_type,
               env.env.common_bridge, backend_id)
    try_run(cmd)


@roles("cyclades")
def setup_vncauthproxy():
    debug(env.host, " * Setting up vncauthproxy...")
    install_package("snf-vncauthproxy")
    cmd = """
    echo CHUID="www-data:nogroup" >> /etc/default/vncauthproxy
    rm /var/log/vncauthproxy/vncauthproxy.log
    """
    try_run(cmd)
    try_run("/etc/init.d/vncauthproxy restart")


@roles("client")
def setup_kamaki():
    debug(env.host, "Setting up kamaki client...")
    with settings(hide("everything")):
        try_run("ping -c1 accounts." + env.env.domain)
        try_run("ping -c1 cyclades." + env.env.domain)
        try_run("ping -c1 pithos." + env.env.domain)

    with settings(host_string=env.env.db.ip):
        uid, user_auth_token, user_uuid = \
            get_auth_token_from_db(env.env.user_email)

    install_package("python-progress")
    install_package("kamaki")
    cmd = """
    kamaki config set cloud.default.url "https://{0}/astakos/identity/v2.0/"
    kamaki config set cloud.default.token {1}
    """.format(env.env.accounts.fqdn, user_auth_token)
    try_run(cmd)
    try_run("kamaki file create images")


@roles("client")
def upload_image(image="debian_base.diskdump"):
    debug(env.host, " * Uploading initial image to pithos...")
    image = "debian_base.diskdump"
    try_run("wget {0} -O /tmp/{1}".format(env.env.debian_base_url, image))
    try_run("kamaki file upload --container images /tmp/{0} {0}".format(image))


@roles("client")
def register_image(image="debian_base.diskdump"):
    debug(env.host, " * Register image to plankton...")
    # with settings(host_string=env.env.db.ip):
    #     uid, user_auth_token, user_uuid = \
    #        get_auth_token_from_db(env.env.user_email)

    image_location = "images:{0}".format(image)
    cmd = """
    sleep 5
    kamaki image register "Debian Base" {0} --public --disk-format=diskdump \
            --property OSFAMILY=linux --property ROOT_PARTITION=1 \
            --property description="Debian Squeeze Base System" \
            --property size=450M --property kernel=2.6.32 \
            --property GUI="No GUI" --property sortorder=1 \
            --property USERS=root --property OS=debian
    """.format(image_location)
    try_run(cmd)


@roles("client")
def setup_burnin():
    debug(env.host, "Setting up burnin testing tool...")
    install_package("kamaki")
    install_package("snf-tools")


@roles("pithos")
def add_image_locally():
    debug(env.host,
          " * Getting image locally in order snf-image to use it directly..")
    image = "debian_base.diskdump"
    try_run("wget {0} -O {1}/{2}".format(
            env.env.debian_base_url, env.env.image_dir, image))


@roles("master")
def gnt_instance_add(name="test"):
    debug(env.host, " * Adding test instance to Ganeti...")
    osp = """img_passwd=gamwtosecurity,\
img_format=diskdump,img_id=debian_base,\
img_properties='{"OSFAMILY":"linux"\,"ROOT_PARTITION":"1"}'"""
    cmd = """
    gnt-instance add  -o snf-image+default --os-parameters {0} \
            -t plain --disk 0:size=1G --no-name-check --no-ip-check \
            --net 0:ip=pool,network=test --no-install \
            --hypervisor-parameters kvm:machine_version=pc-1.0 {1}
    """.format(osp, name)
    try_run(cmd)


@roles("master")
def gnt_network_add(name="test", subnet="10.0.0.0/26", gw="10.0.0.1",
                    mode="bridged", link="br0"):
    debug(env.host, " * Adding test network to Ganeti...")
    cmd = """
    gnt-network add --network={1} --gateway={2} {0}
    gnt-network connect {0} {3} {4}
    """.format(name, subnet, gw, mode, link)
    try_run(cmd)


@roles("ips")
def test():
    debug(env.host, "Testing...")
    try_run("hostname && date")
