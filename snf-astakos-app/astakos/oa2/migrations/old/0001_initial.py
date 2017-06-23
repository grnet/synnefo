# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'RedirectUrl'
        db.create_table('oa2_redirecturl', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oa2.Client'], on_delete=models.PROTECT)),
            ('is_default', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=200)),
        ))
        db.send_create_signal('oa2', ['RedirectUrl'])

        # Adding unique constraint on 'RedirectUrl', fields ['client', 'url']
        db.create_unique('oa2_redirecturl', ['client_id', 'url'])

        # Adding model 'Client'
        db.create_table('oa2_client', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('identifier', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('secret', self.gf('django.db.models.fields.CharField')(default=None, max_length=255, null=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('type', self.gf('django.db.models.fields.CharField')(default='confidential', max_length=100)),
            ('is_trusted', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('oa2', ['Client'])

        # Adding model 'AuthorizationCode'
        db.create_table('oa2_authorizationcode', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.AstakosUser'], on_delete=models.PROTECT)),
            ('code', self.gf('django.db.models.fields.TextField')()),
            ('redirect_uri', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oa2.Client'], on_delete=models.PROTECT)),
            ('scope', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 11, 19, 0, 0))),
            ('state', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
        ))
        db.send_create_signal('oa2', ['AuthorizationCode'])

        # Adding model 'Token'
        db.create_table('oa2_token', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 11, 19, 0, 0))),
            ('expires_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('token_type', self.gf('django.db.models.fields.CharField')(default='Bearer', max_length=100)),
            ('grant_type', self.gf('django.db.models.fields.CharField')(default='authorization_code', max_length=100)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.AstakosUser'], on_delete=models.PROTECT)),
            ('redirect_uri', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oa2.Client'], on_delete=models.PROTECT)),
            ('scope', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('state', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
        ))
        db.send_create_signal('oa2', ['Token'])


    def backwards(self, orm):
        # Removing unique constraint on 'RedirectUrl', fields ['client', 'url']
        db.delete_unique('oa2_redirecturl', ['client_id', 'url'])

        # Deleting model 'RedirectUrl'
        db.delete_table('oa2_redirecturl')

        # Deleting model 'Client'
        db.delete_table('oa2_client')

        # Deleting model 'AuthorizationCode'
        db.delete_table('oa2_authorizationcode')

        # Deleting model 'Token'
        db.delete_table('oa2_token')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'im.astakosuser': {
            'Meta': {'object_name': 'AstakosUser', '_ormbases': ['auth.User']},
            'accepted_email': ('django.db.models.fields.EmailField', [], {'default': 'None', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'accepted_policy': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'activation_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'date_signed_terms': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'deactivated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'deactivated_reason': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'disturbed_quota': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_credits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_signed_terms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'is_rejected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '4'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'moderated_data': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosUserQuota']", 'symmetrical': 'False'}),
            'rejected_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True'}),
            'verification_code': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'im.astakosuserquota': {
            'Meta': {'unique_together': "(('resource', 'user'),)", 'object_name': 'AstakosUserQuota'},
            'capacity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.resource': {
            'Meta': {'object_name': 'Resource'},
            'allow_in_projects': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'service_origin': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'service_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'uplimit': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'})
        },
        'oa2.authorizationcode': {
            'Meta': {'object_name': 'AuthorizationCode'},
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oa2.Client']", 'on_delete': 'models.PROTECT'}),
            'code': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 11, 19, 0, 0)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'redirect_uri': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'scope': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'state': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']", 'on_delete': 'models.PROTECT'})
        },
        'oa2.client': {
            'Meta': {'object_name': 'Client'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'is_trusted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'confidential'", 'max_length': '100'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'oa2.redirecturl': {
            'Meta': {'ordering': "('is_default',)", 'unique_together': "(('client', 'url'),)", 'object_name': 'RedirectUrl'},
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oa2.Client']", 'on_delete': 'models.PROTECT'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_default': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'})
        },
        'oa2.token': {
            'Meta': {'object_name': 'Token'},
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oa2.Client']", 'on_delete': 'models.PROTECT'}),
            'code': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 11, 19, 0, 0)'}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {}),
            'grant_type': ('django.db.models.fields.CharField', [], {'default': "'authorization_code'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'redirect_uri': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'scope': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'state': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'token_type': ('django.db.models.fields.CharField', [], {'default': "'Bearer'", 'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']", 'on_delete': 'models.PROTECT'})
        }
    }

    complete_apps = ['oa2']