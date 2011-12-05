# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SynnefoUser'
        db.create_table('db_synnefouser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('credit', self.gf('django.db.models.fields.IntegerField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('db', ['SynnefoUser'])

        # Adding model 'Image'
        db.create_table('db_image', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('sourcevm', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.VirtualMachine'], null=True)),
        ))
        db.send_create_signal('db', ['Image'])

        # Adding model 'ImageMetadata'
        db.create_table('db_imagemetadata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('meta_key', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('meta_value', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.Image'])),
        ))
        db.send_create_signal('db', ['ImageMetadata'])

        # Adding model 'Limit'
        db.create_table('db_limit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('value', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('db', ['Limit'])

        # Adding model 'Flavor'
        db.create_table('db_flavor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cpu', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('ram', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('disk', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('db', ['Flavor'])

        # Adding unique constraint on 'Flavor', fields ['cpu', 'ram', 'disk']
        db.create_unique('db_flavor', ['cpu', 'ram', 'disk'])

        # Adding model 'FlavorCost'
        db.create_table('db_flavorcost', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cost_active', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('cost_inactive', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('effective_from', self.gf('django.db.models.fields.DateTimeField')()),
            ('flavor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.Flavor'])),
        ))
        db.send_create_signal('db', ['FlavorCost'])

        # Adding model 'VirtualMachine'
        db.create_table('db_virtualmachine', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('charged', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2011, 4, 12, 13, 36, 55, 200332))),
            ('sourceimage', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.Image'])),
            ('hostid', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('ipfour', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
            ('ipsix', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('flavor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.Flavor'])),
            ('deleted', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('suspended', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('action', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
            ('operstate', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
            ('backendjobid', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('backendopcode', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
            ('backendjobstatus', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
            ('backendlogmsg', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('db', ['VirtualMachine'])

        # Adding model 'VirtualMachineGroup'
        db.create_table('db_virtualmachinegroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'])),
        ))
        db.send_create_signal('db', ['VirtualMachineGroup'])

        # Adding M2M table for field machines on 'VirtualMachineGroup'
        db.create_table('db_virtualmachinegroup_machines', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('virtualmachinegroup', models.ForeignKey(orm['db.virtualmachinegroup'], null=False)),
            ('virtualmachine', models.ForeignKey(orm['db.virtualmachine'], null=False))
        ))
        db.create_unique('db_virtualmachinegroup_machines', ['virtualmachinegroup_id', 'virtualmachine_id'])

        # Adding model 'VirtualMachineMetadata'
        db.create_table('db_virtualmachinemetadata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('meta_key', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('meta_value', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('vm', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.VirtualMachine'])),
        ))
        db.send_create_signal('db', ['VirtualMachineMetadata'])

        # Adding model 'Debit'
        db.create_table('db_debit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('when', self.gf('django.db.models.fields.DateTimeField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'])),
            ('vm', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.VirtualMachine'])),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('db', ['Debit'])

        # Adding model 'Disk'
        db.create_table('db_disk', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('size', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('vm', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.VirtualMachine'], null=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'], null=True, blank=True)),
        ))
        db.send_create_signal('db', ['Disk'])


    def backwards(self, orm):
        
        # Deleting model 'SynnefoUser'
        db.delete_table('db_synnefouser')

        # Deleting model 'Image'
        db.delete_table('db_image')

        # Deleting model 'ImageMetadata'
        db.delete_table('db_imagemetadata')

        # Deleting model 'Limit'
        db.delete_table('db_limit')

        # Deleting model 'Flavor'
        db.delete_table('db_flavor')

        # Removing unique constraint on 'Flavor', fields ['cpu', 'ram', 'disk']
        db.delete_unique('db_flavor', ['cpu', 'ram', 'disk'])

        # Deleting model 'FlavorCost'
        db.delete_table('db_flavorcost')

        # Deleting model 'VirtualMachine'
        db.delete_table('db_virtualmachine')

        # Deleting model 'VirtualMachineGroup'
        db.delete_table('db_virtualmachinegroup')

        # Removing M2M table for field machines on 'VirtualMachineGroup'
        db.delete_table('db_virtualmachinegroup_machines')

        # Deleting model 'VirtualMachineMetadata'
        db.delete_table('db_virtualmachinemetadata')

        # Deleting model 'Debit'
        db.delete_table('db_debit')

        # Deleting model 'Disk'
        db.delete_table('db_disk')


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
        'db.synnefouser': {
            'Meta': {'object_name': 'SynnefoUser'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'credit': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.virtualmachine': {
            'Meta': {'object_name': 'VirtualMachine'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendjobid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'backendjobstatus': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendlogmsg': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'backendopcode': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'charged': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 12, 13, 36, 55, 200332)'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'hostid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipfour': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'ipsix': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
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
