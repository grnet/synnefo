# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from astakos.im.tests.common import *


class TestProjects(TestCase):
    """
    Test projects.
    """
    def setUp(self):
        # astakos resources
        self.resource = Resource.objects.create(name="astakos.pending_app",
                                                uplimit=0,
                                                allow_in_projects=False,
                                                service_type="astakos")

        # custom service resources
        self.resource = Resource.objects.create(name="service1.resource",
                                                uplimit=100,
                                                service_type="service1")
        self.admin = get_local_user("projects-admin@synnefo.org")
        self.admin.uuid = 'uuid1'
        self.admin.save()

        self.user = get_local_user("user@synnefo.org")
        self.member = get_local_user("member@synnefo.org")
        self.member2 = get_local_user("member2@synnefo.org")

        self.admin_client = get_user_client("projects-admin@synnefo.org")
        self.user_client = get_user_client("user@synnefo.org")
        self.member_client = get_user_client("member@synnefo.org")
        self.member2_client = get_user_client("member2@synnefo.org")

        quotas.qh_sync_users(AstakosUser.objects.all())

    def tearDown(self):
        Service.objects.all().delete()
        ProjectApplication.objects.all().delete()
        Project.objects.all().delete()
        AstakosUser.objects.all().delete()

    @im_settings(PROJECT_ADMINS=['uuid1'])
    def test_application_limit(self):
        # user cannot create a project
        r = self.user_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_list'))
        self.assertContains(r, "You are not allowed to create a new project")

        # but admin can
        r = self.admin_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_add'))

    @im_settings(PROJECT_ADMINS=['uuid1'])
    def test_allow_in_project(self):
        dfrom = datetime.now()
        dto = datetime.now() + timedelta(days=30)

        # astakos.pending_uplimit allow_in_project flag is False
        # we shouldn't be able to create a project application using this
        # resource.
        application_data = {
            'name': 'project.synnefo.org',
            'homepage': 'https://www.synnefo.org',
            'start_date': dfrom.strftime("%Y-%m-%d"),
            'end_date': dto.strftime("%Y-%m-%d"),
            'member_join_policy': 2,
            'member_leave_policy': 1,
            'service1.resource_uplimit': 100,
            'is_selected_service1.resource': "1",
            'astakos.pending_app_uplimit': 100,
            'is_selected_accounts': "1",
            'user': self.user.pk
        }
        form = forms.ProjectApplicationForm(data=application_data)
        # form is invalid
        self.assertEqual(form.is_valid(), False)

        del application_data['astakos.pending_app_uplimit']
        del application_data['is_selected_accounts']
        form = forms.ProjectApplicationForm(data=application_data)
        self.assertEqual(form.is_valid(), True)

    @im_settings(PROJECT_ADMINS=['uuid1'])
    def test_applications(self):
        # let user have 2 pending applications
        quotas.add_base_quota(self.user, 'astakos.pending_app', 2)

        r = self.user_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_add'))

        # user fills the project application form
        post_url = reverse('project_add') + '?verify=1'
        dfrom = datetime.now()
        dto = datetime.now() + timedelta(days=30)
        application_data = {
            'name': 'project.synnefo.org',
            'homepage': 'https://www.synnefo.org',
            'start_date': dfrom.strftime("%Y-%m-%d"),
            'end_date': dto.strftime("%Y-%m-%d"),
            'member_join_policy': 2,
            'member_leave_policy': 1,
            'service1.resource_uplimit': 100,
            'is_selected_service1.resource': "1",
            'user': self.user.pk
        }
        r = self.user_client.post(post_url, data=application_data, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['form'].is_valid(), True)

        # confirm request
        post_url = reverse('project_add') + '?verify=0&edit=0'
        r = self.user_client.post(post_url, data=application_data, follow=True)
        self.assertContains(r, "The project application has been received")
        self.assertRedirects(r, reverse('project_list'))
        self.assertEqual(ProjectApplication.objects.count(), 1)
        app1 = ProjectApplication.objects.filter().order_by('pk')[0]
        app1_id = app1.pk
        project1_id = app1.chain_id

        # create another one
        application_data['name'] = 'project2.synnefo.org'
        r = self.user_client.post(post_url, data=application_data, follow=True)
        app2 = ProjectApplication.objects.filter().order_by('pk')[1]
        project2_id = app2.chain_id

        # no more applications (LIMIT is 2)
        r = self.user_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_list'))
        self.assertContains(r, "You are not allowed to create a new project")

        # login
        self.admin_client.get(reverse("edit_profile"))
        # admin approves
        r = self.admin_client.post(reverse('project_app_approve',
                                           kwargs={'application_id': app1_id}),
                                   follow=True)
        self.assertEqual(r.status_code, 200)

        # project created
        self.assertEqual(Project.objects.count(), 1)

        # login
        self.member_client.get(reverse("edit_profile"))
        # cannot join project2 (not approved yet)
        join_url = reverse("project_join", kwargs={'chain_id': project2_id})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 403)

        # can join app1
        self.member_client.get(reverse("edit_profile"))
        join_url = reverse("project_join", kwargs={'chain_id': project1_id})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 200)

        memberships = ProjectMembership.objects.all()
        self.assertEqual(len(memberships), 1)
        memb_id = memberships[0].id

        reject_member_url = reverse('project_reject_member',
                                    kwargs={'chain_id': project1_id, 'memb_id':
                                            memb_id})
        accept_member_url = reverse('project_accept_member',
                                    kwargs={'chain_id': project1_id, 'memb_id':
                                            memb_id})

        # only project owner is allowed to reject
        r = self.member_client.post(reject_member_url, follow=True)
        self.assertContains(r, "You do not have the permissions")
        self.assertEqual(r.status_code, 200)

        # user (owns project) rejects membership
        r = self.user_client.post(reject_member_url, follow=True)
        self.assertEqual(ProjectMembership.objects.count(), 0)

        # user rejoins
        self.member_client.get(reverse("edit_profile"))
        join_url = reverse("project_join", kwargs={'chain_id': project1_id})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 200)
        memberships = ProjectMembership.objects.all()
        self.assertEqual(len(memberships), 1)
        memb_id = memberships[0].id

        accept_member_url = reverse('project_accept_member',
                                    kwargs={'chain_id': project1_id, 'memb_id':
                                            memb_id})

        # user (owns project) accepts membership
        r = self.user_client.post(accept_member_url, follow=True)
        self.assertEqual(ProjectMembership.objects.count(), 1)
        membership = ProjectMembership.objects.get()
        self.assertEqual(membership.state, ProjectMembership.ACCEPTED)

        user_quotas = quotas.get_users_quotas([self.member])
        resource = 'service1.resource'
        newlimit = user_quotas[self.member.uuid]['system'][resource]['limit']
        # 100 from initial uplimit + 100 from project
        self.assertEqual(newlimit, 200)

        remove_member_url = reverse('project_remove_member',
                                    kwargs={'chain_id': project1_id, 'memb_id':
                                            membership.id})
        r = self.user_client.post(remove_member_url, follow=True)
        self.assertEqual(r.status_code, 200)

        user_quotas = quotas.get_users_quotas([self.member])
        resource = 'service1.resource'
        newlimit = user_quotas[self.member.uuid]['system'][resource]['limit']
        # 200 - 100 from project
        self.assertEqual(newlimit, 100)

        # support email gets rendered in emails content
        for mail in get_mailbox('user@synnefo.org'):
            self.assertTrue(settings.CONTACT_EMAIL in \
                            mail.message().as_string())
