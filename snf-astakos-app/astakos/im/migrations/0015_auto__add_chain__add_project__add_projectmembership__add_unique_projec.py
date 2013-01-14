# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Removing unique constraint on 'AstakosUser', fields ['third_party_identifier', 'provider']
        try:
            db.delete_unique('im_astakosuser', ['third_party_identifier', 'provider'])
        except:
            pass

        # Adding model 'Chain'
        db.create_table('im_chain', (
            ('chain', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('im', ['Chain'])

        # Adding model 'Project'
        db.create_table('im_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.OneToOneField')(related_name='project', unique=True, to=orm['im.ProjectApplication'])),
            ('last_approval_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('deactivation_reason', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('deactivation_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=80, db_index=True)),
            ('is_modified', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True)),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=1, db_index=True)),
        ))
        db.send_create_signal('im', ['Project'])

        # Adding model 'ProjectMembership'
        db.create_table('im_projectmembership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.AstakosUser'])),
            ('request_date', self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2013, 1, 11, 12, 54, 30, 986304))),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.Project'])),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('is_pending', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(related_name='memberships', null=True, to=orm['im.ProjectApplication'])),
            ('pending_application', self.gf('django.db.models.fields.related.ForeignKey')(related_name='pending_memebrships', null=True, to=orm['im.ProjectApplication'])),
            ('pending_serial', self.gf('django.db.models.fields.BigIntegerField')(null=True, db_index=True)),
            ('acceptance_date', self.gf('django.db.models.fields.DateField')(null=True, db_index=True)),
            ('leave_request_date', self.gf('django.db.models.fields.DateField')(null=True)),
        ))
        db.send_create_signal('im', ['ProjectMembership'])

        # Adding unique constraint on 'ProjectMembership', fields ['person', 'project']
        db.create_unique('im_projectmembership', ['person_id', 'project_id'])

        # Adding model 'ResourceMetadata'
        db.create_table('im_resourcemetadata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('im', ['ResourceMetadata'])

        # Adding model 'AstakosUserAuthProvider'
        db.create_table('im_astakosuserauthprovider', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('affiliation', self.gf('django.db.models.fields.CharField')(default=None, max_length=255, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='auth_providers', to=orm['im.AstakosUser'])),
            ('module', self.gf('django.db.models.fields.CharField')(default='local', max_length=255)),
            ('identifier', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('auth_backend', self.gf('django.db.models.fields.CharField')(default='astakos', max_length=255)),
            ('info_data', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('im', ['AstakosUserAuthProvider'])

        # Adding unique constraint on 'AstakosUserAuthProvider', fields ['identifier', 'module', 'user']
        db.create_unique('im_astakosuserauthprovider', ['identifier', 'module', 'user_id'])

        # Adding model 'Serial'
        db.create_table('im_serial', (
            ('serial', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('im', ['Serial'])

        # Adding model 'Resource'
        db.create_table('im_resource', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.Service'])),
            ('desc', self.gf('django.db.models.fields.TextField')(null=True)),
            ('unit', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('group', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
        ))
        db.send_create_signal('im', ['Resource'])

        # Adding M2M table for field meta on 'Resource'
        db.create_table('im_resource_meta', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('resource', models.ForeignKey(orm['im.resource'], null=False)),
            ('resourcemetadata', models.ForeignKey(orm['im.resourcemetadata'], null=False))
        ))
        db.create_unique('im_resource_meta', ['resource_id', 'resourcemetadata_id'])

        # Adding unique constraint on 'Resource', fields ['name', 'service']
        db.create_unique('im_resource', ['name', 'service_id'])

        # Adding model 'SessionCatalog'
        db.create_table('im_sessioncatalog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('session_key', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sessions', null=True, to=orm['im.AstakosUser'])),
        ))
        db.send_create_signal('im', ['SessionCatalog'])

        # Adding model 'ProjectMembershipHistory'
        db.create_table('im_projectmembershiphistory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.BigIntegerField')()),
            ('project', self.gf('django.db.models.fields.BigIntegerField')()),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.datetime.now)),
            ('reason', self.gf('django.db.models.fields.IntegerField')()),
            ('serial', self.gf('django.db.models.fields.BigIntegerField')()),
        ))
        db.send_create_signal('im', ['ProjectMembershipHistory'])

        # Adding model 'AstakosUserQuota'
        db.create_table('im_astakosuserquota', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('capacity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('quantity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('export_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('import_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.Resource'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.AstakosUser'])),
        ))
        db.send_create_signal('im', ['AstakosUserQuota'])

        # Adding unique constraint on 'AstakosUserQuota', fields ['resource', 'user']
        db.create_unique('im_astakosuserquota', ['resource_id', 'user_id'])

        # Adding model 'ProjectResourceGrant'
        db.create_table('im_projectresourcegrant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.Resource'])),
            ('project_application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.ProjectApplication'], null=True)),
            ('project_capacity', self.gf('synnefo.lib.db.intdecimalfield.IntDecimalField')(default=100000000000000000000000000000000L, max_digits=38, decimal_places=0)),
            ('project_import_limit', self.gf('synnefo.lib.db.intdecimalfield.IntDecimalField')(default=100000000000000000000000000000000L, max_digits=38, decimal_places=0)),
            ('project_export_limit', self.gf('synnefo.lib.db.intdecimalfield.IntDecimalField')(default=100000000000000000000000000000000L, max_digits=38, decimal_places=0)),
            ('member_capacity', self.gf('synnefo.lib.db.intdecimalfield.IntDecimalField')(default=100000000000000000000000000000000L, max_digits=38, decimal_places=0)),
            ('member_import_limit', self.gf('synnefo.lib.db.intdecimalfield.IntDecimalField')(default=100000000000000000000000000000000L, max_digits=38, decimal_places=0)),
            ('member_export_limit', self.gf('synnefo.lib.db.intdecimalfield.IntDecimalField')(default=100000000000000000000000000000000L, max_digits=38, decimal_places=0)),
        ))
        db.send_create_signal('im', ['ProjectResourceGrant'])

        # Adding unique constraint on 'ProjectResourceGrant', fields ['resource', 'project_application']
        db.create_unique('im_projectresourcegrant', ['resource_id', 'project_application_id'])

        # Adding model 'PendingThirdPartyUser'
        db.create_table('im_pendingthirdpartyuser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('third_party_identifier', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('provider', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('affiliation', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('info', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
        ))
        db.send_create_signal('im', ['PendingThirdPartyUser'])

        # Adding unique constraint on 'PendingThirdPartyUser', fields ['provider', 'third_party_identifier']
        db.create_unique('im_pendingthirdpartyuser', ['provider', 'third_party_identifier'])

        # Adding model 'ProjectApplication'
        db.create_table('im_projectapplication', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('applicant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects_applied', to=orm['im.AstakosUser'])),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects_owned', to=orm['im.AstakosUser'])),
            ('chain', self.gf('django.db.models.fields.IntegerField')()),
            ('precursor_application', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['im.ProjectApplication'], unique=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=255, null=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('member_join_policy', self.gf('django.db.models.fields.IntegerField')()),
            ('member_leave_policy', self.gf('django.db.models.fields.IntegerField')()),
            ('limit_on_members_number', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('issue_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('im', ['ProjectApplication'])

        # Adding unique constraint on 'ProjectApplication', fields ['chain', 'id']
        db.create_unique('im_projectapplication', ['chain', 'id'])

        # Adding field 'Service.order'
        db.add_column('im_service', 'order', self.gf('django.db.models.fields.PositiveIntegerField')(default=0), keep_default=False)

        # Adding index on 'Service', fields ['name']
        db.create_index('im_service', ['name'])

        # Adding field 'AstakosUser.uuid'
        db.add_column('im_astakosuser', 'uuid', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True, null=True), keep_default=False)

        # Adding field 'AstakosUser.disturbed_quota'
        db.add_column('im_astakosuser', 'disturbed_quota', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True), keep_default=False)

        # Changing field 'AstakosUser.affiliation'
        db.alter_column('im_astakosuser', 'affiliation', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'AstakosUser.provider'
        db.alter_column('im_astakosuser', 'provider', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changin field 'auth_user.username'
        db.alter_column('auth_user', 'username', models.CharField(max_length=75))


    def backwards(self, orm):

        # Removing index on 'Service', fields ['name']
        db.delete_index('im_service', ['name'])

        # Removing unique constraint on 'ProjectApplication', fields ['chain', 'id']
        db.delete_unique('im_projectapplication', ['chain', 'id'])

        # Removing unique constraint on 'PendingThirdPartyUser', fields ['provider', 'third_party_identifier']
        db.delete_unique('im_pendingthirdpartyuser', ['provider', 'third_party_identifier'])

        # Removing unique constraint on 'ProjectResourceGrant', fields ['resource', 'project_application']
        db.delete_unique('im_projectresourcegrant', ['resource_id', 'project_application_id'])

        # Removing unique constraint on 'AstakosUserQuota', fields ['resource', 'user']
        db.delete_unique('im_astakosuserquota', ['resource_id', 'user_id'])

        # Removing unique constraint on 'Resource', fields ['name', 'service']
        db.delete_unique('im_resource', ['name', 'service_id'])

        # Removing unique constraint on 'AstakosUserAuthProvider', fields ['identifier', 'module', 'user']
        db.delete_unique('im_astakosuserauthprovider', ['identifier', 'module', 'user_id'])

        # Removing unique constraint on 'ProjectMembership', fields ['person', 'project']
        db.delete_unique('im_projectmembership', ['person_id', 'project_id'])

        # Deleting model 'Chain'
        db.delete_table('im_chain')

        # Deleting model 'Project'
        db.delete_table('im_project')

        # Deleting model 'ProjectMembership'
        db.delete_table('im_projectmembership')

        # Deleting model 'ResourceMetadata'
        db.delete_table('im_resourcemetadata')

        # Deleting model 'AstakosUserAuthProvider'
        db.delete_table('im_astakosuserauthprovider')

        # Deleting model 'Serial'
        db.delete_table('im_serial')

        # Deleting model 'Resource'
        db.delete_table('im_resource')

        # Removing M2M table for field meta on 'Resource'
        db.delete_table('im_resource_meta')

        # Deleting model 'SessionCatalog'
        db.delete_table('im_sessioncatalog')

        # Deleting model 'ProjectMembershipHistory'
        db.delete_table('im_projectmembershiphistory')

        # Deleting model 'AstakosUserQuota'
        db.delete_table('im_astakosuserquota')

        # Deleting model 'ProjectResourceGrant'
        db.delete_table('im_projectresourcegrant')

        # Deleting model 'PendingThirdPartyUser'
        db.delete_table('im_pendingthirdpartyuser')

        # Deleting model 'ProjectApplication'
        db.delete_table('im_projectapplication')

        # Deleting field 'Service.order'
        db.delete_column('im_service', 'order')

        # Deleting field 'AstakosUser.uuid'
        db.delete_column('im_astakosuser', 'uuid')

        # Deleting field 'AstakosUser.disturbed_quota'
        db.delete_column('im_astakosuser', 'disturbed_quota')

        for u in orm.AstakosUser.objects.all():
            u.affiliation = u.affiliation or ''
            u.save()

        # Changing field 'AstakosUser.affiliation'
        db.alter_column('im_astakosuser', 'affiliation', self.gf('django.db.models.fields.CharField')(default='', max_length=255))

        # Changing field 'AstakosUser.provider'
        db.alter_column('im_astakosuser', 'provider', self.gf('django.db.models.fields.CharField')(default='', max_length=255))

        # Adding unique constraint on 'AstakosUser', fields ['third_party_identifier', 'provider']
        db.create_unique('im_astakosuser', ['third_party_identifier', 'provider'])

        # Changin field 'auth_user.username'
        db.alter_column('auth_user', 'username', models.CharField(max_length=30))


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
        'im.additionalmail': {
            'Meta': {'object_name': 'AdditionalMail'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.approvalterms': {
            'Meta': {'object_name': 'ApprovalTerms'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 1, 11, 12, 54, 30, 982234)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.astakosuser': {
            'Meta': {'object_name': 'AstakosUser', '_ormbases': ['auth.User']},
            'activation_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'date_signed_terms': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'disturbed_quota': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_credits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_signed_terms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '4'}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosUserQuota']", 'symmetrical': 'False'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'third_party_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True'})
        },
        'im.astakosuserauthprovider': {
            'Meta': {'ordering': "('module', 'created')", 'unique_together': "(('identifier', 'module', 'user'),)", 'object_name': 'AstakosUserAuthProvider'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'auth_backend': ('django.db.models.fields.CharField', [], {'default': "'astakos'", 'max_length': '255'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'info_data': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'default': "'local'", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'auth_providers'", 'to': "orm['im.AstakosUser']"})
        },
        'im.astakosuserquota': {
            'Meta': {'unique_together': "(('resource', 'user'),)", 'object_name': 'AstakosUserQuota'},
            'capacity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'export_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.chain': {
            'Meta': {'object_name': 'Chain'},
            'chain': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'im.emailchange': {
            'Meta': {'object_name': 'EmailChange'},
            'activation_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'new_email_address': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'requested_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 1, 11, 12, 54, 30, 983023)'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'emailchanges'", 'unique': 'True', 'to': "orm['im.AstakosUser']"})
        },
        'im.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'code': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'}),
            'consumed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inviter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invitations_sent'", 'null': 'True', 'to': "orm['im.AstakosUser']"}),
            'is_consumed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'realname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'im.pendingthirdpartyuser': {
            'Meta': {'unique_together': "(('provider', 'third_party_identifier'),)", 'object_name': 'PendingThirdPartyUser'},
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'third_party_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'im.project': {
            'Meta': {'object_name': 'Project'},
            'application': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'project'", 'unique': 'True', 'to': "orm['im.ProjectApplication']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {}),
            'deactivation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'deactivation_reason': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'is_modified': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'last_approval_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.AstakosUser']", 'through': "orm['im.ProjectMembership']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80', 'db_index': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1', 'db_index': 'True'})
        },
        'im.projectapplication': {
            'Meta': {'unique_together': "(('chain', 'id'),)", 'object_name': 'ProjectApplication'},
            'applicant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_applied'", 'to': "orm['im.AstakosUser']"}),
            'chain': ('django.db.models.fields.IntegerField', [], {}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'limit_on_members_number': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'member_join_policy': ('django.db.models.fields.IntegerField', [], {}),
            'member_leave_policy': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_owned'", 'to': "orm['im.AstakosUser']"}),
            'precursor_application': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['im.ProjectApplication']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'resource_grants': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.ProjectResourceGrant']", 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'im.projectmembership': {
            'Meta': {'unique_together': "(('person', 'project'),)", 'object_name': 'ProjectMembership'},
            'acceptance_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True'}),
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'memberships'", 'null': 'True', 'to': "orm['im.ProjectApplication']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_pending': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'leave_request_date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'pending_application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pending_memebrships'", 'null': 'True', 'to': "orm['im.ProjectApplication']"}),
            'pending_serial': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Project']"}),
            'request_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2013, 1, 11, 12, 54, 30, 986304)'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'})
        },
        'im.projectmembershiphistory': {
            'Meta': {'object_name': 'ProjectMembershipHistory'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.BigIntegerField', [], {}),
            'project': ('django.db.models.fields.BigIntegerField', [], {}),
            'reason': ('django.db.models.fields.IntegerField', [], {}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'im.projectresourcegrant': {
            'Meta': {'unique_together': "(('resource', 'project_application'),)", 'object_name': 'ProjectResourceGrant'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member_capacity': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'member_export_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'member_import_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'project_application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.ProjectApplication']", 'null': 'True'}),
            'project_capacity': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'project_export_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'project_import_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"})
        },
        'im.resource': {
            'Meta': {'unique_together': "(('name', 'service'),)", 'object_name': 'Resource'},
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.ResourceMetadata']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Service']"}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        },
        'im.resourcemetadata': {
            'Meta': {'object_name': 'ResourceMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.serial': {
            'Meta': {'object_name': 'Serial'},
            'serial': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'im.service': {
            'Meta': {'ordering': "('order',)", 'object_name': 'Service'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'icon': ('django.db.models.fields.FilePathField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('django.db.models.fields.FilePathField', [], {'max_length': '100'})
        },
        'im.sessioncatalog': {
            'Meta': {'object_name': 'SessionCatalog'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sessions'", 'null': 'True', 'to': "orm['im.AstakosUser']"})
        }
    }

    complete_apps = ['im']
