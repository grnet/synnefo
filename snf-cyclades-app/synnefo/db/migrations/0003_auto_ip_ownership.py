# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sys

ASSOCIATE = "associate"
DISASSOCIATE = "disassociate"


def migrate_ip_address_log(apps, schema_editor):
    IPAddressLog = apps.get_model("db", "IPAddressLog")
    IPAddressHistory = apps.get_model("db", "IPAddressHistory")
    VirtualMachine = apps.get_model("db", "VirtualMachine")
    vm_owners = dict(VirtualMachine.objects.values_list("id", "userid"))
    history = []

    for ip_log in IPAddressLog.objects.all():
        for (action, date) in [(ASSOCIATE, ip_log.allocated_at),
                               (DISASSOCIATE, ip_log.released_at)]:
            if date is not None:
                history.append(IPAddressHistory(
                    address=ip_log.address,
                    server_id=ip_log.server_id,
                    network_id=ip_log.network_id,
                    user_id=vm_owners[ip_log.server_id],
                    action=action,
                    action_date=date,
                    action_reason=("migration from IPAddressLog %s"
                                   % ip_log.id)))
    IPAddressHistory.objects.bulk_create(history)
    print "Created %s IP history entries." % len(history)


def migrate_ips_and_nics(apps, schema_editor):
    IPAddress = apps.get_model("db", "IPAddress")
    NetworkInterface = apps.get_model("db", "NetworkInterface")
    nics = NetworkInterface.objects.all().select_related("machine").exclude(
        userid=models.F("machine__userid"))
    for nic in nics:
        print "Changing owner of nic %s from '%s' to '%s'." % (
            nic.id, nic.userid, nic.machine.userid)
        nic.userid = nic.machine.userid
        nic.save()

    ips = IPAddress.objects.filter(shared_to_project=False).select_related(
        "nic__machine").exclude(userid=models.F("nic__machine__userid"))
    for ip in ips:
        print "Changing owner of IP '%s' from '%s' to '%s'." % (
            ip.address, ip.userid, ip.nic.machine.userid)
        ip.userid = ip.nic.machine.userid
        if ip.project is not None:
            print "Changing project of IP '%s' from '%s' to '%s'." \
                % (ip.address, ip.project, ip.nic.machine.project)
            ip.project = ip.nic.machine.project
        ip.save()


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0002_ipaddresshistory'),
    ]

    operations = [
        migrations.RunPython(migrate_ip_address_log),
        migrations.RunPython(migrate_ips_and_nics),
    ]
