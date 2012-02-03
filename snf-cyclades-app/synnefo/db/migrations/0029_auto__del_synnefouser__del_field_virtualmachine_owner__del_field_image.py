# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'SynnefoUser'
        db.delete_table('db_synnefouser')

        # Deleting field 'VirtualMachine.owner'
        db.delete_column('db_virtualmachine', 'owner_id')

        # Deleting field 'Image.owner'
        db.delete_column('db_image', 'owner_id')

        # Changing field 'Image.userid'
        db.alter_column('db_image', 'userid', self.gf('django.db.models.fields.CharField')(max_length=100, null=True))

        # Deleting field 'Network.owner'
        db.delete_column('db_network', 'owner_id')

        # Changing field 'Network.userid'
        db.alter_column('db_network', 'userid', self.gf('django.db.models.fields.CharField')(max_length=100, null=True))


    def backwards(self, orm):
        
        # Adding model 'SynnefoUser'
        db.create_table('db_synnefouser', (
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('realname', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('auth_token', self.gf('django.db.models.fields.CharField')(max_length=32, null=True)),
            ('tmp_auth_token_expires', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('tmp_auth_token', self.gf('django.db.models.fields.CharField')(max_length=32, null=True)),
            ('auth_token_expires', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('auth_token_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='ACTIVE', max_length=30)),
            ('uniq', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('db', ['SynnefoUser'])

        # User chose to not deal with backwards NULL issues for 'VirtualMachine.owner'
        raise RuntimeError("Cannot reverse this migration. 'VirtualMachine.owner' and its values cannot be restored.")

        # Adding field 'Image.owner'
        db.add_column('db_image', 'owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'], null=True, blank=True), keep_default=False)

        # Changing field 'Image.userid'
        db.alter_column('db_image', 'userid', self.gf('django.db.models.fields.CharField')(max_length=100))

        # Adding field 'Network.owner'
        db.add_column('db_network', 'owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser'], null=True), keep_default=False)

        # Changing field 'Network.userid'
        db.alter_column('db_network', 'userid', self.gf('django.db.models.fields.CharField')(max_length=100))


    models = {
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
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sourcevm': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.VirtualMachine']", 'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
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
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
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
        'db.virtualmachine': {
            'Meta': {'object_name': 'VirtualMachine'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendjobid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'backendjobstatus': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendlogmsg': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'backendopcode': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'buildpercentage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'charged': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 1, 23, 15, 32, 51, 475392)'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'hostid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'operstate': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
