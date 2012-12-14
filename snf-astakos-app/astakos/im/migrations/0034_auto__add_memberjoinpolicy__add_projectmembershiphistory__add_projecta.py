# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Resource', fields ['name']
        db.delete_unique('im_resource', ['name'])

        # Adding model 'MemberJoinPolicy'
        db.create_table('im_memberjoinpolicy', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('policy', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('im', ['MemberJoinPolicy'])

        # Adding model 'ProjectMembershipHistory'
        db.create_table('im_projectmembershiphistory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.AstakosUser'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.Project'])),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.datetime.now)),
            ('reason', self.gf('django.db.models.fields.IntegerField')()),
            ('serial', self.gf('django.db.models.fields.BigIntegerField')()),
        ))
        db.send_create_signal('im', ['ProjectMembershipHistory'])

        # Adding model 'ProjectApplication'
        db.create_table('im_projectapplication', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('applicant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='my_project_applications', to=orm['im.AstakosUser'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='own_project_applications', to=orm['im.AstakosUser'])),
            ('precursor_application', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['im.ProjectApplication'], unique=True, null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='Unknown', max_length=80)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('member_join_policy', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.MemberJoinPolicy'])),
            ('member_leave_policy', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.MemberLeavePolicy'])),
            ('limit_on_members_number', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('issue_date', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('im', ['ProjectApplication'])

        # Adding model 'Project'
        db.create_table('im_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('new_state', self.gf('django.db.models.fields.BigIntegerField')()),
            ('synced_state', self.gf('django.db.models.fields.BigIntegerField')()),
            ('sync_status', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('application', self.gf('django.db.models.fields.related.OneToOneField')(related_name='project', unique=True, null=True, to=orm['im.ProjectApplication'])),
            ('last_application_approved', self.gf('django.db.models.fields.related.OneToOneField')(related_name='last_project', unique=True, to=orm['im.ProjectApplication'])),
            ('last_approval_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('termination_start_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('termination_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=80, db_index=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='Unknown', max_length=80)),
        ))
        db.send_create_signal('im', ['Project'])

        # Adding model 'ProjectMembership'
        db.create_table('im_projectmembership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('new_state', self.gf('django.db.models.fields.BigIntegerField')()),
            ('synced_state', self.gf('django.db.models.fields.BigIntegerField')()),
            ('sync_status', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.AstakosUser'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.Project'])),
            ('request_date', self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2012, 12, 13, 16, 50, 58, 29637))),
            ('acceptance_date', self.gf('django.db.models.fields.DateField')(null=True, db_index=True)),
            ('leave_request_date', self.gf('django.db.models.fields.DateField')(null=True)),
        ))
        db.send_create_signal('im', ['ProjectMembership'])

        # Adding unique constraint on 'ProjectMembership', fields ['person', 'project']
        db.create_unique('im_projectmembership', ['person_id', 'project_id'])

        # Adding model 'MemberLeavePolicy'
        db.create_table('im_memberleavepolicy', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('policy', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('im', ['MemberLeavePolicy'])

        # Adding model 'ProjectResourceGrant'
        db.create_table('im_projectresourcegrant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.Resource'])),
            ('project_application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['im.ProjectApplication'], blank=True)),
            ('project_capacity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('project_import_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('project_export_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('member_capacity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('member_import_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('member_export_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
        ))
        db.send_create_signal('im', ['ProjectResourceGrant'])

        # Adding unique constraint on 'ProjectResourceGrant', fields ['resource', 'project_application']
        db.create_unique('im_projectresourcegrant', ['resource_id', 'project_application_id'])

        # Removing index on 'Resource', fields ['name']
        db.delete_index('im_resource', ['name'])

        # Adding unique constraint on 'Resource', fields ['name', 'service']
        db.create_unique('im_resource', ['name', 'service_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Resource', fields ['name', 'service']
        db.delete_unique('im_resource', ['name', 'service_id'])

        # Adding index on 'Resource', fields ['name']
        db.create_index('im_resource', ['name'])

        # Removing unique constraint on 'ProjectResourceGrant', fields ['resource', 'project_application']
        db.delete_unique('im_projectresourcegrant', ['resource_id', 'project_application_id'])

        # Removing unique constraint on 'ProjectMembership', fields ['person', 'project']
        db.delete_unique('im_projectmembership', ['person_id', 'project_id'])

        # Deleting model 'MemberJoinPolicy'
        db.delete_table('im_memberjoinpolicy')

        # Deleting model 'ProjectMembershipHistory'
        db.delete_table('im_projectmembershiphistory')

        # Deleting model 'ProjectApplication'
        db.delete_table('im_projectapplication')

        # Deleting model 'Project'
        db.delete_table('im_project')

        # Deleting model 'ProjectMembership'
        db.delete_table('im_projectmembership')

        # Deleting model 'MemberLeavePolicy'
        db.delete_table('im_memberleavepolicy')

        # Deleting model 'ProjectResourceGrant'
        db.delete_table('im_projectresourcegrant')

        # Adding unique constraint on 'Resource', fields ['name']
        db.create_unique('im_resource', ['name'])


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
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 12, 13, 16, 50, 58, 1095)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.astakosgroup': {
            'Meta': {'object_name': 'AstakosGroup', '_ormbases': ['auth.Group']},
            'approval_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 12, 13, 16, 50, 57, 993338)'}),
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'estimated_participants': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.Group']", 'unique': 'True', 'primary_key': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'issue_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'kind': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.GroupKind']"}),
            'max_participants': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'moderation_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosGroupQuota']", 'blank': 'True'})
        },
        'im.astakosgroupquota': {
            'Meta': {'unique_together': "(('resource', 'group'),)", 'object_name': 'AstakosGroupQuota'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosGroup']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'limit': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'uplimit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'})
        },
        'im.astakosuser': {
            'Meta': {'unique_together': "(('provider', 'third_party_identifier'),)", 'object_name': 'AstakosUser', '_ormbases': ['auth.User']},
            'activation_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'astakos_groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.AstakosGroup']", 'symmetrical': 'False', 'through': "orm['im.Membership']", 'blank': 'True'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'date_signed_terms': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'disturbed_quota': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_credits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_signed_terms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '100'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'owner': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'owner'", 'null': 'True', 'to': "orm['im.AstakosGroup']"}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosUserQuota']", 'symmetrical': 'False'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'third_party_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        'im.astakosuserauthprovider': {
            'Meta': {'unique_together': "(('identifier', 'module', 'user'),)", 'object_name': 'AstakosUserAuthProvider'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'auth_backend': ('django.db.models.fields.CharField', [], {'default': "'astakos'", 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'default': "'local'", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'auth_providers'", 'to': "orm['im.AstakosUser']"})
        },
        'im.astakosuserquota': {
            'Meta': {'unique_together': "(('resource', 'user'),)", 'object_name': 'AstakosUserQuota'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'limit': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'uplimit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.emailchange': {
            'Meta': {'object_name': 'EmailChange'},
            'activation_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'new_email_address': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'requested_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 12, 13, 16, 50, 58, 2937)'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'emailchange_user'", 'unique': 'True', 'to': "orm['im.AstakosUser']"})
        },
        'im.groupkind': {
            'Meta': {'object_name': 'GroupKind'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
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
        'im.memberjoinpolicy': {
            'Meta': {'object_name': 'MemberJoinPolicy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'policy': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
        },
        'im.memberleavepolicy': {
            'Meta': {'object_name': 'MemberLeavePolicy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'policy': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
        },
        'im.membership': {
            'Meta': {'unique_together': "(('person', 'group'),)", 'object_name': 'Membership'},
            'date_joined': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'date_requested': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2012, 12, 13, 16, 50, 57, 998898)', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.pendingthirdpartyuser': {
            'Meta': {'unique_together': "(('provider', 'third_party_identifier'),)", 'object_name': 'PendingThirdPartyUser'},
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'third_party_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'im.project': {
            'Meta': {'object_name': 'Project'},
            'application': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'project'", 'unique': 'True', 'null': 'True', 'to': "orm['im.ProjectApplication']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_application_approved': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'last_project'", 'unique': 'True', 'to': "orm['im.ProjectApplication']"}),
            'last_approval_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.AstakosUser']", 'through': "orm['im.ProjectMembership']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80', 'db_index': 'True'}),
            'new_state': ('django.db.models.fields.BigIntegerField', [], {}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'Unknown'", 'max_length': '80'}),
            'sync_status': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'synced_state': ('django.db.models.fields.BigIntegerField', [], {}),
            'termination_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'termination_start_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'im.projectapplication': {
            'Meta': {'object_name': 'ProjectApplication'},
            'applicant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'my_project_applications'", 'to': "orm['im.AstakosUser']"}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_date': ('django.db.models.fields.DateTimeField', [], {}),
            'limit_on_members_number': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'member_join_policy': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.MemberJoinPolicy']"}),
            'member_leave_policy': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.MemberLeavePolicy']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'own_project_applications'", 'to': "orm['im.AstakosUser']"}),
            'precursor_application': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['im.ProjectApplication']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'resource_grants': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.ProjectResourceGrant']", 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'Unknown'", 'max_length': '80'})
        },
        'im.projectmembership': {
            'Meta': {'unique_together': "(('person', 'project'),)", 'object_name': 'ProjectMembership'},
            'acceptance_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'leave_request_date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'new_state': ('django.db.models.fields.BigIntegerField', [], {}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Project']"}),
            'request_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2012, 12, 13, 16, 50, 58, 29637)'}),
            'sync_status': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'synced_state': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'im.projectmembershiphistory': {
            'Meta': {'object_name': 'ProjectMembershipHistory'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Project']"}),
            'reason': ('django.db.models.fields.IntegerField', [], {}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'im.projectresourcegrant': {
            'Meta': {'unique_together': "(('resource', 'project_application'),)", 'object_name': 'ProjectResourceGrant'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member_capacity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'member_export_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'member_import_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'project_application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.ProjectApplication']", 'blank': 'True'}),
            'project_capacity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'project_export_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'project_import_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
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
        'im.service': {
            'Meta': {'object_name': 'Service'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'icon': ('django.db.models.fields.FilePathField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
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
