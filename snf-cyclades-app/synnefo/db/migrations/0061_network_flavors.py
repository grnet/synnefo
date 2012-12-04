# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for net in orm.Network.objects.all():
            if net.flavor == 'PUBLIC_ROUTED':
                net.mode = 'routed'
                net.flavor = 'IP_LESS_ROUTED'
                net.tags = 'ip-less-routed'
            if net.flavor == 'PRIVATE_MAC_FILTERED':
                net.mode = 'bridged'
                net.flavor = 'MAC_FILTERED'
                net.tags = 'private-filtered'
            if net.flavor == 'PRIVATE_PHYSICAL_VLAN':
                net.mode = 'bridged'
                net.flavor = 'PHYSICAL_VLAN'
                net.tags = 'physical-vlan'
            if net.flavor == 'CUSTOM_ROUTED':
                net.mode = 'routed'
                net.flavor = 'CUSTOM'
                net.tags = None
            if net.flavor == 'CUSTOM_BRIDGED':
                net.mode = 'bridged'
                net.flavor = 'CUSTOM'
                net.tags = None
            net.save()


    def backwards(self, orm):
        "Write your backwards methods here."
        for net in orm.Network.objects.all():
            if net.flavor == 'CUSTOM' and net.mode == 'bridged':
                net.flavor = 'CUSTOM_BRIDGED'
            if net.flavor == 'CUSTOM' and net.mode == 'routed':
                net.flavor = 'CUSTOM_ROUTED'
            if net.flavor == 'IP_LESS_ROUTED':
                net.flavor = 'PUBLIC_ROUTED'
            if net.flavor == 'MAC_FILTERED':
                net.flavor = 'PRIVATE_MAC_FILTERED'
            if net.flavor == 'PHYSICAL_VLAN':
                net.flavor = 'PRIVATE_PHYSICAL_VLAN'
            net.save()


    models = {
        'db.backend': {
            'Meta': {'object_name': 'Backend'},
            'clustername': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'ctotal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'dfree': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'drained': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'dtotal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'unique': 'True'}),
            'mfree': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'mtotal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'offline': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'password_hash': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'pinst_cnt': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5080'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'db.backendnetwork': {
            'Meta': {'unique_together': "(('network', 'backend'),)", 'object_name': 'BackendNetwork'},
            'backend': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'networks'", 'to': "orm['db.Backend']"}),
            'backendjobid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'backendjobstatus': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendlogmsg': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'backendopcode': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendtime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(1, 1, 1, 0, 0)'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mac_prefix': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'backend_networks'", 'to': "orm['db.Network']"}),
            'operstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.bridgepooltable': {
            'Meta': {'object_name': 'BridgePoolTable'},
            'available_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'base': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offset': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'reserved_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'db.flavor': {
            'Meta': {'unique_together': "(('cpu', 'ram', 'disk', 'disk_template'),)", 'object_name': 'Flavor'},
            'cpu': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'disk': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'disk_template': ('django.db.models.fields.CharField', [], {'default': "'plain'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ram': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'db.ippooltable': {
            'Meta': {'object_name': 'IPPoolTable'},
            'available_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'base': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offset': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'reserved_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'db.macprefixpooltable': {
            'Meta': {'object_name': 'MacPrefixPoolTable'},
            'available_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'base': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offset': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'reserved_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'db.network': {
            'Meta': {'object_name': 'Network'},
            'action': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '32', 'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'dhcp': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'gateway': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'gateway6': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'mac_prefix': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'machines': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['db.VirtualMachine']", 'through': "orm['db.NetworkInterface']", 'symmetrical': 'False'}),
            'mode': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'pool': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'network'", 'unique': 'True', 'null': 'True', 'to': "orm['db.IPPoolTable']"}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'network'", 'null': 'True', 'to': "orm['db.QuotaHolderSerial']"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '32'}),
            'subnet': ('django.db.models.fields.CharField', [], {'default': "'10.0.0.0/24'", 'max_length': '32'}),
            'subnet6': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'db_index': 'True'})
        },
        'db.networkinterface': {
            'Meta': {'object_name': 'NetworkInterface'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dirty': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'firewall_profile': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'ipv4': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True'}),
            'ipv6': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'mac': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.VirtualMachine']"}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.Network']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.quotaholderserial': {
            'Meta': {'object_name': 'QuotaHolderSerial'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'pending': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'rejected': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True', 'db_index': 'True'})
        },
        'db.virtualmachine': {
            'Meta': {'object_name': 'VirtualMachine'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backend': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'virtual_machines'", 'null': 'True', 'to': "orm['db.Backend']"}),
            'backend_hash': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'backendjobid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'backendjobstatus': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendlogmsg': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'backendopcode': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendtime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(1, 1, 1, 0, 0)'}),
            'buildpercentage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'hostid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'operstate': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'virtual_machine'", 'null': 'True', 'to': "orm['db.QuotaHolderSerial']"}),
            'suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        'db.virtualmachinediagnostic': {
            'Meta': {'object_name': 'VirtualMachineDiagnostic'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'details': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'diagnostics'", 'to': "orm['db.VirtualMachine']"}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'source_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'db.virtualmachinemetadata': {
            'Meta': {'unique_together': "(('meta_key', 'vm'),)", 'object_name': 'VirtualMachineMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta_key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'meta_value': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'vm': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'metadata'", 'to': "orm['db.VirtualMachine']"})
        }
    }

    complete_apps = ['db']
