# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'NetworkInterface'
        db.create_table('db_networkinterface', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('machine', self.gf('django.db.models.fields.related.ForeignKey')(related_name='nics', to=orm['db.VirtualMachine'])),
            ('network', self.gf('django.db.models.fields.related.ForeignKey')(related_name='nics', to=orm['db.Network'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('index', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('mac', self.gf('django.db.models.fields.CharField')(max_length=17, null=True)),
            ('ipv4', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True)),
            ('ipv6', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('firewall_profile', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
        ))
        db.send_create_signal('db', ['NetworkInterface'])

        # Deleting field 'VirtualMachine.ipsix'
        db.delete_column('db_virtualmachine', 'ipsix')

        # Deleting field 'VirtualMachine.ipfour'
        db.delete_column('db_virtualmachine', 'ipfour')

        # Adding field 'Network.state'
        db.add_column('db_network', 'state', self.gf('django.db.models.fields.CharField')(default='ACTIVE', max_length=30), keep_default=False)

        # Adding field 'Network.public'
        db.add_column('db_network', 'public', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)

        # Removing M2M table for field machines on 'Network'
        db.delete_table('db_network_machines')


    def backwards(self, orm):
        
        # Deleting model 'NetworkInterface'
        db.delete_table('db_networkinterface')

        # Adding field 'VirtualMachine.ipsix'
        db.add_column('db_virtualmachine', 'ipsix', self.gf('django.db.models.fields.CharField')(default='', max_length=100), keep_default=False)

        # Adding field 'VirtualMachine.ipfour'
        db.add_column('db_virtualmachine', 'ipfour', self.gf('django.db.models.fields.IPAddressField')(default='', max_length=15), keep_default=False)

        # Deleting field 'Network.state'
        db.delete_column('db_network', 'state')

        # Deleting field 'Network.public'
        db.delete_column('db_network', 'public')

        # Adding M2M table for field machines on 'Network'
        db.create_table('db_network_machines', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('network', models.ForeignKey(orm['db.network'], null=False)),
            ('virtualmachine', models.ForeignKey(orm['db.virtualmachine'], null=False))
        ))
        db.create_unique('db_network_machines', ['network_id', 'virtualmachine_id'])


    models = {
        'db.debit': {
            'Meta': {'object_name': 'Debit'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']"}),
            'vm': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.VirtualMachine']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {})
        },
        'db.disk': {
            'Meta': {'object_name': 'Disk'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']", 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'vm': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.VirtualMachine']", 'null': 'True', 'blank': 'True'})
        },
        'db.flavor': {
            'Meta': {'unique_together': "(('cpu', 'ram', 'disk'),)", 'object_name': 'Flavor'},
            'cpu': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'disk': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ram': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'db.flavorcost': {
            'Meta': {'object_name': 'FlavorCost'},
            'cost_active': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'cost_inactive': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'effective_from': ('django.db.models.fields.DateTimeField', [], {}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'db.image': {
            'Meta': {'object_name': 'Image'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']", 'null': 'True', 'blank': 'True'}),
            'sourcevm': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.VirtualMachine']", 'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.imagemetadata': {
            'Meta': {'object_name': 'ImageMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Image']"}),
            'meta_key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'meta_value': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'db.limit': {
            'Meta': {'object_name': 'Limit'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']"}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        'db.network': {
            'Meta': {'object_name': 'Network'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'machines': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['db.VirtualMachine']", 'through': "orm['db.NetworkInterface']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']"}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.networkinterface': {
            'Meta': {'object_name': 'NetworkInterface'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'firewall_profile': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'ipv4': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True'}),
            'ipv6': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'mac': ('django.db.models.fields.CharField', [], {'max_length': '17', 'null': 'True'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.VirtualMachine']"}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.Network']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.synnefouser': {
            'Meta': {'object_name': 'SynnefoUser'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'credit': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'realname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uniq': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.virtualmachine': {
            'Meta': {'object_name': 'VirtualMachine'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendjobid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'backendjobstatus': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendlogmsg': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'backendopcode': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'charged': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 25, 10, 10, 33, 528191)'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'hostid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'operstate': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']"}),
            'sourceimage': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Image']"}),
            'suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.virtualmachinegroup': {
            'Meta': {'object_name': 'VirtualMachineGroup'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'machines': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['db.VirtualMachine']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.virtualmachinemetadata': {
            'Meta': {'object_name': 'VirtualMachineMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta_key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'meta_value': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'vm': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.VirtualMachine']"})
        }
    }

    complete_apps = ['db']
