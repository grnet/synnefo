# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'User'
        db.create_table('im_user', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uniq', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('realname', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('email', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('affiliation', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('state', self.gf('django.db.models.fields.CharField')(default='ACTIVE', max_length=16)),
            ('level', self.gf('django.db.models.fields.IntegerField')(default=4)),
            ('invitations', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('password', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('is_admin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('auth_token', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('auth_token_created', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('auth_token_expires', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')()),
            ('updated', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('im', ['User'])

        # Adding model 'Invitation'
        db.create_table('im_invitation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('inviter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='invitations_sent', null=True, to=orm['im.User'])),
            ('realname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('uniq', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('code', self.gf('django.db.models.fields.BigIntegerField')(db_index=True)),
            ('is_accepted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('accepted', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('im', ['Invitation'])


    def backwards(self, orm):
        
        # Deleting model 'User'
        db.delete_table('im_user')

        # Deleting model 'Invitation'
        db.delete_table('im_invitation')


    models = {
        'im.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'accepted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inviter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invitations_sent'", 'null': 'True', 'to': "orm['im.User']"}),
            'is_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'realname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uniq': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.user': {
            'Meta': {'object_name': 'User'},
            'affiliation': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'email': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '4'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'realname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'ACTIVE'", 'max_length': '16'}),
            'uniq': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['im']
