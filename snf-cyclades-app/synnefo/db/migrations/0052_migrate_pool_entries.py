# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from synnefo import settings
from bitarray import bitarray
from base64 import b64encode

def create_empty_pool(size):
    ba = bitarray(size)
    ba.setall(True)
    return ba

def bitarray_to_string(bitarray_):
    return b64encode(bitarray_.tostring())

def validate_mac(value):
    hex_ = value.replace(":", "")
    bin_ = bin(int(hex_, 16))[2:].zfill(8)
    return bin_[6] == '1' and bin_[7] == '0'

def mac_from_index(base, index):
    """Convert number to mac prefix

    """
    a = hex(int(base.replace(":", ""), 16) + index).replace("0x", '')
    mac_prefix = ":".join([a[x:x + 2] for x in xrange(0, len(a), 2)])
    return mac_prefix

class Migration(DataMigration):
    
    def forwards(self, orm):
        "Write your forwards methods here."

        # Migrate Bridge Pool
        bridges = orm.BridgePool.objects.all()
        if bridges:
            try:
                pool_prefix = settings.PRIVATE_PHYSICAL_VLAN_BRIDGE_PREFIX
            except AttributeError:
                pool_prefix = ''

            try:
                pool_length = settings.PRIVATE_PHYSICAL_VLAN_MAX_NUMBER
            except:
                pool_length = len(bridges)

            reserved = create_empty_pool(pool_length)
            available = create_empty_pool(pool_length)

            for bridge in bridges:
                if not bridge.available:
                    # Bridge indexes in old BridgePool
                    available[bridge.index - 1] = False
            available_map = bitarray_to_string(available)
            reserved_map = bitarray_to_string(reserved)

            orm.BridgePoolTable.objects.create(available_map=available_map,
                                               reserved_map=reserved_map,
                                               size=pool_length,
                                               base=pool_prefix)


        mac_prefixes = orm.MacPrefixPool.objects.all()
        if mac_prefixes:
            try:
                macp_base = settings.MAC_POOL_BASE
            except AttributeError:
                first = mac_prefixes[0]
                first[-1]= '0'
                macp_base =  first

            try:
                macp_length = settings.MAC_POOL_LIMIT
            except:
                macp_length = len(bridges)

            reserved = create_empty_pool(macp_length)
            available = create_empty_pool(macp_length)

            for macp in mac_prefixes:
                if not macp.available:
                    available[macp.index - 1] = False

            for index in range(0, macp_length):
                mac = mac_from_index(macp_base, index)
                if not validate_mac(mac):
                    reserved[index] = False

            available_map = bitarray_to_string(available)
            reserved_map = bitarray_to_string(reserved)

            orm.MacPrefixPoolTable.objects.create(available_map=available_map,
                                               reserved_map=reserved_map,
                                               size=macp_length,
                                               base=macp_base)

    def backwards(self, orm):
        "Write your backwards methods here."
        raise RuntimeError("Can not reverse this migrations")

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
        'db.bridgepool': {
            'Meta': {'object_name': 'BridgePool'},
            'available': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
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
        'db.macprefixpool': {
            'Meta': {'object_name': 'MacPrefixPool'},
            'available': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
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
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'dhcp': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'gateway': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'gateway6': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'mac_prefix': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'machines': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['db.VirtualMachine']", 'through': "orm['db.NetworkInterface']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'reservations': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '32'}),
            'subnet': ('django.db.models.fields.CharField', [], {'default': "'10.0.0.0/24'", 'max_length': '32'}),
            'subnet6': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'PRIVATE_PHYSICAL_VLAN'", 'max_length': '50'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'})
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
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'hostid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'operstate': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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
