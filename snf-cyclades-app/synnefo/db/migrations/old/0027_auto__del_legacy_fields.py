# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'FlavorCost'
        db.delete_table('db_flavorcost')

        # Deleting model 'Invitations'
        db.delete_table('db_invitations')

        # Deleting model 'VirtualMachineGroup'
        db.delete_table('db_virtualmachinegroup')

        # Removing M2M table for field machines on 'VirtualMachineGroup'
        db.delete_table('db_virtualmachinegroup_machines')

        # Deleting model 'Limit'
        db.delete_table('db_limit')

        # Deleting model 'Debit'
        db.delete_table('db_debit')

        # Deleting field 'SynnefoUser.credit'
        db.delete_column('db_synnefouser', 'credit')

        # Deleting field 'SynnefoUser.max_invitations'
        db.delete_column('db_synnefouser', 'max_invitations')


    def backwards(self, orm):
        
        # Adding model 'FlavorCost'
        db.create_table('db_flavorcost', (
            ('cost_active', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('effective_from', self.gf('django.db.models.fields.DateTimeField')()),
            ('flavor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.Flavor'])),
            ('cost_inactive', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('db', ['FlavorCost'])

        # Adding model 'Invitations'
        db.create_table('db_invitations', (
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(related_name='source', to=orm['db.SynnefoUser'])),
            ('level', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(related_name='target', to=orm['db.SynnefoUser'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('accepted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('db', ['Invitations'])

        # Adding model 'VirtualMachineGroup'
        db.create_table('db_virtualmachinegroup', (
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('db', ['VirtualMachineGroup'])

        # Adding M2M table for field machines on 'VirtualMachineGroup'
        db.create_table('db_virtualmachinegroup_machines', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('virtualmachinegroup', models.ForeignKey(orm['db.virtualmachinegroup'], null=False)),
            ('virtualmachine', models.ForeignKey(orm['db.virtualmachine'], null=False))
        ))
        db.create_unique('db_virtualmachinegroup_machines', ['virtualmachinegroup_id', 'virtualmachine_id'])

        # Adding model 'Limit'
        db.create_table('db_limit', (
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.IntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('db', ['Limit'])

        # Adding model 'Debit'
        db.create_table('db_debit', (
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('when', self.gf('django.db.models.fields.DateTimeField')()),
            ('vm', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.VirtualMachine'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('db', ['Debit'])

        # Adding field 'SynnefoUser.credit'
        db.add_column('db_synnefouser', 'credit', self.gf('django.db.models.fields.IntegerField')(default=0), keep_default=False)

        # Adding field 'SynnefoUser.max_invitations'
        db.add_column('db_synnefouser', 'max_invitations', self.gf('django.db.models.fields.IntegerField')(null=True), keep_default=False)


    models = {
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
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'disk': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'disk_template': ('django.db.models.fields.CharField', [], {'default': "'drbd'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ram': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'db.image': {
            'Meta': {'object_name': 'Image'},
            'backend_id': ('django.db.models.fields.CharField', [], {'default': "'debian_base'", 'max_length': '50'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'format': ('django.db.models.fields.CharField', [], {'default': "'dump'", 'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']", 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sourcevm': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.VirtualMachine']", 'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.imagemetadata': {
            'Meta': {'unique_together': "(('meta_key', 'image'),)", 'object_name': 'ImageMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'metadata'", 'to': "orm['db.Image']"}),
            'meta_key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'meta_value': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'db.network': {
            'Meta': {'object_name': 'Network'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['db.NetworkLink']"}),
            'machines': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['db.VirtualMachine']", 'through': "orm['db.NetworkInterface']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']", 'null': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.networkinterface': {
            'Meta': {'object_name': 'NetworkInterface'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'firewall_profile': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'ipv4': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True'}),
            'ipv6': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'mac': ('django.db.models.fields.CharField', [], {'max_length': '17', 'null': 'True'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.VirtualMachine']"}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.Network']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.networklink': {
            'Meta': {'object_name': 'NetworkLink'},
            'available': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['db.Network']"})
        },
        'db.synnefouser': {
            'Meta': {'object_name': 'SynnefoUser'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'realname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'ACTIVE'", 'max_length': '30'}),
            'tmp_auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'tmp_auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
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
            'buildpercentage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'charged': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 1, 23, 14, 29, 44, 160884)'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'hostid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'operstate': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']"}),
            'suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
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
