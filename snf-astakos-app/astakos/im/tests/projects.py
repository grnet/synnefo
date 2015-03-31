# -*- coding: utf-8 -*-
# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from astakos.im.tests.common import *


NotFound = type('NotFound', (), {})


def find(f, seq):
    for item in seq:
        if f(item):
            return item
    return NotFound


def get_pending_apps(user):
    return quotas.get_user_quotas(user)\
        [user.base_project.uuid]['astakos.pending_app']['usage']


class ProjectAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        component1 = Component.objects.create(name="comp1")
        register.add_service(component1, "σέρβις1", "type1", [])
        # custom service resources
        resource11 = {"name": u"σέρβις1.ρίσορς11",
                      "desc": u"ρίσορς11 desc",
                      "service_type": "type1",
                      "service_origin": u"σέρβις1",
                      "ui_visible": True}
        r, _ = register.add_resource(resource11)
        register.update_base_default(r, 100)
        resource12 = {"name": u"σέρβις1.resource12",
                      "desc": "resource12 desc",
                      "service_type": "type1",
                      "service_origin": u"σέρβις1",
                      "unit": "bytes"}
        r, _ = register.add_resource(resource12)
        register.update_base_default(r, 1024)

        # create user
        self.user1 = get_local_user("test@grnet.gr")
        self.user2 = get_local_user("test2@grnet.gr")
        self.user2.uuid = "uuid2"
        self.user2.save()
        self.user3 = get_local_user("test3@grnet.gr")

        astakos = Component.objects.create(name="astakos")
        register.add_service(astakos, "astakos_account", "account", [])
        # create another service
        pending_app = {"name": "astakos.pending_app",
                       "desc": "pend app desc",
                       "service_type": "account",
                       "service_origin": "astakos_account",
                       "ui_visible": False,
                       "api_visible": False}
        r, _ = register.add_resource(pending_app)
        register.update_base_default(r, 3)
        request = {"resources": {r.name: {"member_capacity": 3,
                                          "project_capacity": 3}}}
        functions.modify_projects_in_bulk(Q(is_base=True), request)

    def create(self, app, headers):
        dump = json.dumps(app)
        r = self.client.post(reverse("api_projects"), dump,
                             content_type="application/json", **headers)
        body = json.loads(r.content)
        return r.status_code, body

    def modify(self, app, project_id, headers):
        dump = json.dumps(app)
        kwargs = {"project_id": project_id}
        r = self.client.put(reverse("api_project", kwargs=kwargs), dump,
                            content_type="application/json", **headers)
        body = json.loads(r.content)
        return r.status_code, body

    def project_action(self, project_id, action, app_id=None, headers=None):
        action_data = {"reason": ""}
        if app_id is not None:
            action_data["app_id"] = app_id
        action = json.dumps({action: action_data})
        r = self.client.post(reverse("api_project_action",
                                     kwargs={"project_id": project_id}),
                             action, content_type="application/json",
                             **headers)
        return r.status_code

    def memb_action(self, memb_id, action, headers):
        action = json.dumps({action: "reason"})
        r = self.client.post(reverse("api_membership_action",
                                     kwargs={"memb_id": memb_id}), action,
                             content_type="application/json", **headers)
        return r.status_code

    def join(self, project_id, headers):
        action = {"join": {"project": project_id}}
        req = json.dumps(action)
        r = self.client.post(reverse("api_memberships"), req,
                             content_type="application/json", **headers)
        body = json.loads(r.content)
        return r.status_code, body

    def enroll(self, project_id, user, headers):
        action = {
            "enroll": {
                "project": project_id,
                "user": user.email,
            }
        }
        req = json.dumps(action)
        r = self.client.post(reverse("api_memberships"), req,
                             content_type="application/json", **headers)
        body = json.loads(r.content)
        return r.status_code, body

    @im_settings(PROJECT_ADMINS=["uuid2"])
    def test_projects(self):
        client = self.client
        h_owner = {"HTTP_X_AUTH_TOKEN": self.user1.auth_token}
        h_admin = {"HTTP_X_AUTH_TOKEN": self.user2.auth_token}
        h_plain = {"HTTP_X_AUTH_TOKEN": self.user3.auth_token}
        r = client.get(reverse("api_project", kwargs={"project_id": 1}))
        self.assertEqual(r.status_code, 401)

        r = client.get(reverse("api_project", kwargs={"project_id": 1}),
                       **h_owner)
        self.assertEqual(r.status_code, 404)
        r = client.get(reverse("api_membership", kwargs={"memb_id": 100}),
                       **h_owner)
        self.assertEqual(r.status_code, 404)

        status = self.memb_action(1, "accept", h_admin)
        self.assertEqual(status, 409)

        app1 = {"name": "test.pr",
                "description": u"δεσκρίπτιον",
                "end_date": "2113-5-5T20:20:20Z",
                "join_policy": "auto",
                "max_members": 5,
                "resources": {u"σέρβις1.ρίσορς11": {
                    "project_capacity": 1024,
                    "member_capacity": 512}}
                }

        status, body = self.modify(app1, 100, h_owner)
        self.assertEqual(status, 404)

        # Create
        status, body = self.create(app1, h_owner)
        self.assertEqual(status, 201)
        project_id = body["id"]
        app_id = body["application"]

        # Get project
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}),
                       **h_owner)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body["id"], project_id)
        self.assertEqual(body["last_application"]["id"], app_id)
        self.assertEqual(body["last_application"]["state"], "pending")
        self.assertEqual(body["state"], "uninitialized")
        self.assertEqual(body["owner"], self.user1.uuid)
        self.assertEqual(body["description"], u"δεσκρίπτιον")

        # Approve forbidden
        status = self.project_action(project_id, "approve", app_id=app_id,
                                     headers=h_owner)
        self.assertEqual(status, 403)

        # Create another with the same name
        status, body = self.create(app1, h_owner)
        self.assertEqual(status, 201)
        project2_id = body["id"]
        project2_app_id = body["application"]

        # Create yet another, with different name
        app_p3 = copy.deepcopy(app1)
        app_p3["name"] = "new.pr"
        status, body = self.create(app_p3, h_owner)
        self.assertEqual(status, 201)
        project3_id = body["id"]
        project3_app_id = body["application"]

        # No more pending allowed
        status, body = self.create(app_p3, h_owner)
        self.assertEqual(status, 409)

        # Cancel
        status = self.project_action(project3_id, "cancel",
                                     app_id=project3_app_id, headers=h_owner)
        self.assertEqual(status, 200)

        # Get project
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project3_id}),
                       **h_owner)
        body = json.loads(r.content)
        self.assertEqual(body["state"], "deleted")

        # Modify of uninitialized failed
        app2 = {"name": "test.pr",
                "start_date": "2013-5-5T20:20:20Z",
                "end_date": "2113-7-5T20:20:20Z",
                "join_policy": "moderated",
                "leave_policy": "auto",
                "max_members": 3,
                "resources": {u"σέρβις1.ρίσορς11": {
                    "project_capacity": 1024,
                    "member_capacity": 1024}}
                }
        status, body = self.modify(app2, project_id, h_owner)
        self.assertEqual(status, 409)

        # Create the project again
        status, body = self.create(app2, h_owner)
        self.assertEqual(status, 201)
        project_id = body["id"]
        app_id = body["application"]

        # Dismiss failed
        status = self.project_action(project_id, "dismiss", app_id,
                                     headers=h_owner)
        self.assertEqual(status, 409)

        # Deny
        status = self.project_action(project_id, "deny", app_id,
                                     headers=h_admin)
        self.assertEqual(status, 200)

        # Get project
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}),
                       **h_owner)
        body = json.loads(r.content)
        self.assertEqual(body["last_application"]["id"], app_id)
        self.assertEqual(body["last_application"]["state"], "denied")
        self.assertEqual(body["state"], "uninitialized")

        # Dismiss
        status = self.project_action(project_id, "dismiss", app_id,
                                     headers=h_owner)
        self.assertEqual(status, 200)

        # Get project
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}),
                       **h_owner)
        body = json.loads(r.content)
        self.assertEqual(body["last_application"]["id"], app_id)
        self.assertEqual(body["last_application"]["state"], "dismissed")
        self.assertEqual(body["state"], "deleted")

        # Create the project again
        status, body = self.create(app2, h_owner)
        self.assertEqual(status, 201)
        project_id = body["id"]
        app_id = body["application"]

        # Approve
        status = self.project_action(project_id, "approve", app_id,
                                     headers=h_admin)
        self.assertEqual(status, 200)

        # Check memberships
        r = client.get(reverse("api_memberships"), **h_plain)
        body = json.loads(r.content)
        self.assertEqual(len(body), 1)

        # Enroll
        status, body = self.enroll(project_id, self.user3, h_owner)
        self.assertEqual(status, 200)
        m_plain_id = body["id"]

        # Get project
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}),
                       **h_owner)
        body = json.loads(r.content)
        # Join
        status, body = self.join(project_id, h_owner)
        self.assertEqual(status, 200)
        memb_id = body["id"]

        # Check memberships
        r = client.get(reverse("api_memberships"), **h_plain)
        body = json.loads(r.content)
        self.assertEqual(len(body), 2)
        m = find(lambda m: m["project"] == project_id, body)
        self.assertNotEqual(m, NotFound)
        self.assertEqual(m["user"], self.user3.uuid)
        self.assertEqual(m["state"], "accepted")

        r = client.get(reverse("api_memberships"), **h_owner)
        body = json.loads(r.content)
        self.assertEqual(len(body), 3)

        # Check membership
        r = client.get(reverse("api_membership", kwargs={"memb_id": memb_id}),
                       **h_admin)
        m = json.loads(r.content)
        self.assertEqual(m["user"], self.user1.uuid)
        self.assertEqual(m["state"], "requested")
        self.assertEqual(sorted(m["allowed_actions"]),
                         ["accept", "cancel", "reject"])

        r = client.get(reverse("api_membership", kwargs={"memb_id": memb_id}),
                       **h_plain)
        self.assertEqual(r.status_code, 403)

        status = self.memb_action(memb_id, "leave", h_admin)
        self.assertEqual(status, 409)

        status = self.memb_action(memb_id, "cancel", h_owner)
        self.assertEqual(status, 200)

        status, body = self.join(project_id, h_owner)
        self.assertEqual(status, 200)
        self.assertEqual(memb_id, body["id"])

        status = self.memb_action(memb_id, "reject", h_owner)
        self.assertEqual(status, 200)

        status, body = self.join(project_id, h_owner)
        self.assertEqual(status, 200)
        self.assertEqual(memb_id, body["id"])

        status = self.memb_action(memb_id, "accept", h_owner)
        self.assertEqual(status, 200)

        # Enroll fails, already in
        status, body = self.enroll(project_id, self.user1, h_owner)
        self.assertEqual(status, 409)

        # Remove member
        status = self.memb_action(memb_id, "remove", h_owner)
        self.assertEqual(status, 200)

        # Enroll a removed member
        status, body = self.enroll(project_id, self.user1, h_owner)
        self.assertEqual(status, 200)

        # Remove member
        status = self.memb_action(memb_id, "remove", h_owner)
        self.assertEqual(status, 200)

        # Re-join
        status, body = self.join(project_id, h_owner)
        self.assertEqual(status, 200)
        self.assertEqual(memb_id, body["id"])

        # Enroll a requested member
        status, body = self.enroll(project_id, self.user1, h_owner)
        self.assertEqual(status, 200)

        # Enroll fails, already in
        status, body = self.enroll(project_id, self.user1, h_owner)
        self.assertEqual(status, 409)

        # Enroll fails, project does not exist
        status, body = self.enroll(-1, self.user1, h_owner)
        self.assertEqual(status, 409)

        # Get projects
        ## Simple user mode
        r = client.get(reverse("api_projects"), **h_plain)
        body = json.loads(r.content)
        self.assertEqual(len(body), 2)
        p = body[0]
        with assertRaises(KeyError):
            p["pending_application"]

        ## Owner mode
        filters = {"state": "active"}
        r = client.get(reverse("api_projects"), filters, **h_owner)
        body = json.loads(r.content)
        self.assertEqual(len(body), 2)

        filters = {"state": "deleted"}
        r = client.get(reverse("api_projects"), filters, **h_owner)
        body = json.loads(r.content)
        self.assertEqual(len(body), 2)

        filters = {"state": "uninitialized"}
        r = client.get(reverse("api_projects"), filters, **h_owner)
        body = json.loads(r.content)
        self.assertEqual(len(body), 2)

        filters = {"name": "test.pr"}
        r = client.get(reverse("api_projects"), filters, **h_owner)
        body = json.loads(r.content)
        self.assertEqual(len(body), 4)

        filters = {"mode": "member"}
        r = client.get(reverse("api_projects"), filters, **h_owner)
        body = json.loads(r.content)
        self.assertEqual(len(body), 2)

        # Leave failed
        status = self.memb_action(m_plain_id, "leave", h_owner)
        self.assertEqual(status, 403)

        # Leave
        status = self.memb_action(m_plain_id, "leave", h_plain)
        self.assertEqual(status, 200)

        # Suspend failed
        status = self.project_action(project_id, "suspend", headers=h_owner)
        self.assertEqual(status, 403)

        # Unsuspend failed
        status = self.project_action(project_id, "unsuspend", headers=h_admin)
        self.assertEqual(status, 409)

        # Suspend
        status = self.project_action(project_id, "suspend", headers=h_admin)
        self.assertEqual(status, 200)

        # Cannot view project
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}), **h_plain)
        self.assertEqual(r.status_code, 403)

        # Unsuspend
        status = self.project_action(project_id, "unsuspend", headers=h_admin)
        self.assertEqual(status, 200)

        # Cannot approve, project with same name exists
        status = self.project_action(project2_id, "approve", project2_app_id,
                                     headers=h_admin)
        self.assertEqual(status, 409)

        # Terminate
        status = self.project_action(project_id, "terminate", headers=h_admin)
        self.assertEqual(status, 200)

        # Join failed
        status, _ = self.join(project_id, h_admin)
        self.assertEqual(status, 409)

        # Can approve now
        status = self.project_action(project2_id, "approve", project2_app_id,
                                     headers=h_admin)
        self.assertEqual(status, 200)

        # Join new project
        status, body = self.join(project2_id, h_plain)
        self.assertEqual(status, 200)
        m_project2 = body["id"]

        # Get memberships of project
        filters = {"project": project2_id}
        r = client.get(reverse("api_memberships"), filters, **h_owner)
        body = json.loads(r.content)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], m_project2)

        # Remove member
        status = self.memb_action(m_project2, "remove", h_owner)
        self.assertEqual(status, 200)

        # Reinstate failed
        status = self.project_action(project_id, "reinstate", headers=h_admin)
        self.assertEqual(status, 409)

        # Rename
        app2_renamed = copy.deepcopy(app2)
        app2_renamed["name"] = "new.name"
        status, body = self.modify(app2_renamed, project_id, h_owner)
        self.assertEqual(status, 201)
        app2_renamed_id = body["application"]

        # Get project
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}), **h_owner)
        body = json.loads(r.content)
        self.assertEqual(body["last_application"]["id"], app2_renamed_id)
        self.assertEqual(body["state"], "terminated")
        assertIn("deactivation_date", body)
        self.assertEqual(body["last_application"]["state"], "pending")
        self.assertEqual(body["last_application"]["name"], "new.name")
        status = self.project_action(project_id, "approve", app2_renamed_id,
                                     headers=h_admin)
        self.assertEqual(r.status_code, 200)

        # Change homepage
        status, body = self.modify({"homepage": "new.page"},
                                   project_id, h_owner)
        self.assertEqual(status, 201)

        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}), **h_owner)
        body = json.loads(r.content)
        self.assertEqual(body["homepage"], "")
        self.assertEqual(body["last_application"]["homepage"], "new.page")
        homepage_app = body["last_application"]["id"]
        status = self.project_action(project_id, "approve", homepage_app,
                                     headers=h_admin)
        self.assertEqual(r.status_code, 200)
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}), **h_owner)
        body = json.loads(r.content)
        self.assertEqual(body["homepage"], "new.page")

        # Bad requests
        r = client.head(reverse("api_projects"), **h_admin)
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)

        r = client.head(reverse("api_project",
                                kwargs={"project_id": 1}), **h_admin)
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)

        r = client.head(reverse("api_memberships"), **h_admin)
        self.assertEqual(r.status_code, 405)
        self.assertTrue('Allow' in r)

        status = self.project_action(1, "nonex", headers=h_owner)
        self.assertEqual(status, 400)

        action = json.dumps({"suspend": "", "unsuspend": ""})
        r = client.post(reverse("api_project_action",
                                kwargs={"project_id": 1}),
                        action, content_type="application/json", **h_owner)
        self.assertEqual(r.status_code, 400)


        ap_base = {
            "owner": self.user1.uuid,
            "name": "domain.name",
            "join_policy": "auto",
            "leave_policy": "closed",
            "start_date": "2113-01-01T0:0Z",
            "end_date": "2114-01-01T0:0Z",
            "max_members": 0,
            "resources": {
                u"σέρβις1.ρίσορς11": {
                    "member_capacity": 512,
                    "project_capacity": 1024}
                },
            }
        status, body = self.create(ap_base, h_owner)
        project_b_id = body["id"]
        app_b_id = body["application"]
        self.assertEqual(status, 201)

        # Cancel
        status = self.project_action(project_b_id, "cancel",
                                     app_id=app_b_id, headers=h_owner)
        self.assertEqual(status, 200)

        ap = copy.deepcopy(ap_base)
        ap["owner"] = "nonex"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)
        self.assertEqual(body["badRequest"]["message"], "User does not exist.")

        ap = copy.deepcopy(ap_base)
        ap.pop("name")
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["name"] = "non_domain_name"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["name"] = 100 * "domain.name." + ".org"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["join_policy"] = "nonex"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["leave_policy"] = "nonex"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap.pop("end_date")
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["end_date"] = "2000-01-01T0:0Z"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["start_date"] = "nonex"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["max_members"] = -3
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["max_members"] = 2**63
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["homepage"] = 100 * "huge"
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["resources"] = {42: 42}
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["resources"] = {u"σέρβις1.ρίσορς11": {"member_capacity": 512}}
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["resources"] = {u"σέρβις1.ρίσορς11": {"member_capacity": -512,
                                                 "project_capacity": 256}}
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        ap = copy.deepcopy(ap_base)
        ap["resources"] = {u"σέρβις1.ρίσορς11": {"member_capacity": 512,
                                                 "project_capacity": 256}}
        status, body = self.create(ap, h_owner)
        self.assertEqual(status, 400)

        filters = {"state": "nonex"}
        r = client.get(reverse("api_projects"), filters, **h_owner)
        self.assertEqual(r.status_code, 400)

        app = {"max_members": 33, "name": "new.name"}
        status, body = self.modify(app, self.user1.uuid, h_owner)
        self.assertEqual(status, 403)

        app = {"max_members": 33, "name": "new.name"}
        status, body = self.modify(app, self.user1.uuid, h_admin)
        self.assertEqual(status, 409)

        app = {"max_members": 33}
        status, body = self.modify(app, self.user1.uuid, h_admin)
        self.assertEqual(status, 201)

        # directly modify a base project
        with assertRaises(functions.ProjectBadRequest):
            functions.modify_project(self.user1.uuid,
                                     {"description": "new description",
                                      "member_join_policy":
                                      functions.MODERATED_POLICY})
        functions.modify_project(self.user1.uuid,
                                 {"member_join_policy":
                                  functions.MODERATED_POLICY})
        r = client.get(reverse("api_project",
                               kwargs={"project_id": self.user1.uuid}),
                       **h_owner)
        body = json.loads(r.content)
        self.assertEqual(body["join_policy"], "moderated")

        r = self.client.post(reverse("api_projects"), "\xff",
                             content_type="application/json", **h_owner)
        self.assertEqual(r.status_code, 400)

        r = self.client.post(reverse("api_project_action",
                                     kwargs={"project_id": "1234"}),
                             "\"nondict\"", content_type="application/json",
                             **h_owner)
        self.assertEqual(r.status_code, 400)

        r = client.get(reverse("api_project",
                               kwargs={"project_id": u"πρότζεκτ"}),
                       **h_owner)
        self.assertEqual(r.status_code, 404)

        # Check pending app quota integrity
        r = client.get(reverse("api_project",
                               kwargs={"project_id": project_id}),
                       **h_owner)
        body = json.loads(r.content)
        self.assertNotEqual(body['last_application']['state'], 'pending')

        admin_pa0 = get_pending_apps(self.user2)
        owner_pa0 = get_pending_apps(self.user1)

        app = {"max_members": 11}
        status, body = self.modify(app, project_id, h_admin)
        self.assertEqual(status, 201)

        admin_pa1 = get_pending_apps(self.user2)
        owner_pa1 = get_pending_apps(self.user1)
        self.assertEqual(admin_pa1, admin_pa0+1)
        self.assertEqual(owner_pa1, owner_pa0)
        status, body = self.modify(app, project_id, h_owner)
        self.assertEqual(status, 201)

        admin_pa2 = get_pending_apps(self.user2)
        owner_pa2 = get_pending_apps(self.user1)
        self.assertEqual(admin_pa2, admin_pa1-1)
        self.assertEqual(owner_pa2, owner_pa1+1)

        status, body = self.modify(app, project_id, h_owner)
        self.assertEqual(status, 201)

        admin_pa3 = get_pending_apps(self.user2)
        owner_pa3 = get_pending_apps(self.user1)
        self.assertEqual(admin_pa3, admin_pa2)
        self.assertEqual(owner_pa3, owner_pa2)


class TestProjects(TestCase):
    """
    Test projects.
    """
    def setUp(self):
        # astakos resources
        self.resource = Resource.objects.create(name="astakos.pending_app",
                                                uplimit=0,
                                                project_default=0,
                                                ui_visible=False,
                                                api_visible=False,
                                                service_type="astakos")

        # custom service resources
        self.resource = Resource.objects.create(name="service1.resource",
                                                uplimit=100,
                                                project_default=0,
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
    def test_ui_visible(self):
        dfrom = datetime.now()
        dto = datetime.now() + timedelta(days=30)

        # astakos.pending_app ui_visible flag is False
        # we shouldn't be able to create a project application using this
        # resource.
        application_data = {
            'name': 'project.synnefo.org',
            'homepage': 'https://www.synnefo.org',
            'start_date': dfrom.strftime("%Y-%m-%d"),
            'end_date': dto.strftime("%Y-%m-%d"),
            'member_join_policy': 2,
            'member_leave_policy': 1,
            'limit_on_members_number_0': 5,
            'service1.resource_m_uplimit': 100,
            'is_selected_service1.resource': "1",
            'astakos.pending_app_m_uplimit': 100,
            'is_selected_accounts': "1",
            'user': self.user.pk
        }
        form = forms.ProjectApplicationForm(data=application_data)
        # form is invalid
        self.assertEqual(form.is_valid(), False)

        del application_data['astakos.pending_app_m_uplimit']
        del application_data['is_selected_accounts']
        form = forms.ProjectApplicationForm(data=application_data)
        self.assertEqual(form.is_valid(), True)

    @im_settings(PROJECT_ADMINS=['uuid1'])
    def test_applications(self):
        # let user have 2 pending applications

        # TODO figure this out
        request = {
            "resources": {
                "astakos.pending_app": {
                    "member_capacity": 2,
                    "project_capacity": 2}
                }
            }
        functions.modify_project(self.user.uuid, request)

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
            'limit_on_members_number_0': '5',
            'service1.resource_m_uplimit': 10,
            'service1.resource_p_uplimit': 100,
            'is_selected_service1.resource': "1",
            'user': self.user.pk
        }
        r = self.user_client.post(post_url, data=application_data, follow=True)
        self.assertEqual(r.status_code, 200)
        form = r.context['form']
        form.is_valid()
        self.assertEqual(r.context['form'].is_valid(), True)

        application_data['limit_on_members_number'] = 5
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

        # one project per application
        self.assertEqual(Project.objects.filter(is_base=False).count(), 2)

        # login
        self.admin_client.get(reverse("edit_profile"))

        # admin approves
        r = self.admin_client.post(reverse('project_app_approve',
                                           kwargs={
                                            'application_id': app1_id,
                                            'project_uuid': app1.chain.uuid}),
                                   follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Project.objects.filter(is_base=False,
            state=Project.O_ACTIVE).count(), 1)

        # submit a modification
        post_url = reverse('project_modify', args=(app1.chain.uuid,)) + '?verify=0&edit=1'
        modification_data = {
            'name': 'project.synnefo.org',
            'homepage': 'https://www.synnefo.org',
            'start_date': dfrom.strftime("%Y-%m-%d"),
            'end_date': dto.strftime("%Y-%m-%d"),
            'member_join_policy': 2,
            'member_leave_policy': 1,
            'limit_on_members_number_0': '5',
            'service1.resource_m_uplimit': 300,
            'service1.resource_p_uplimit': 100,
            'is_selected_service1.resource': "1",
            'user': self.user.pk
        }
        resp = self.user_client.post(post_url, modification_data)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['form'].is_valid())

        del modification_data['service1.resource_p_uplimit']
        resp = self.user_client.post(post_url, modification_data)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['form'].is_valid())

        modification_data['service1.resource_p_uplimit'] = 100
        modification_data['service1.resource_m_uplimit'] = 3
        post_url = reverse('project_modify', args=(app1.chain.uuid,)) + '?verify=0&edit=0'
        resp = self.user_client.post(post_url, modification_data)
        self.assertEqual(resp.status_code, 302)

        app = ProjectApplication.objects.get(state=ProjectApplication.PENDING,
                                             chain=app1.chain)
        self.assertEqual(app.limit_on_members_number, 5)

        # login
        self.member_client.get(reverse("edit_profile"))
        # cannot join project2 (not approved yet)
        join_url = reverse("project_join", kwargs={
            'project_uuid': app2.chain.uuid})
        r = self.member_client.post(join_url, follow=True)

        # can join project1
        self.member_client.get(reverse("edit_profile"))
        join_url = reverse("project_join", kwargs={
            'project_uuid': app1.chain.uuid})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 200)

        memberships = ProjectMembership.objects.filter(project__is_base=False)
        self.assertEqual(len(memberships), 1)
        memb_id = memberships[0].id

        reject_member_url = reverse('project_reject_member',
                                    kwargs={
                                        'project_uuid': app1.chain.uuid,
                                        'memb_id': memb_id
                                    })
        accept_member_url = reverse('project_accept_member',
                                    kwargs={
                                        'memb_id': memb_id,
                                        'project_uuid': app1.chain.uuid
                                    })

        # only project owner is allowed to reject
        r = self.member_client.post(reject_member_url, follow=True)
        self.assertContains(r, "You do not have the permissions")
        self.assertEqual(r.status_code, 200)

        # user (owns project) rejects membership
        r = self.user_client.post(reject_member_url, follow=True)
        membs = ProjectMembership.objects.any_accepted().filter(
            project__is_base=False)
        self.assertEqual(membs.count(), 0)

        # user rejoins
        self.member_client.get(reverse("edit_profile"))
        join_url = reverse("project_join", kwargs={'project_uuid':
                                                   app1.chain.uuid})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ProjectMembership.objects.requested().count(), 1)

        # user (owns project) accepts membership
        r = self.user_client.post(accept_member_url, follow=True)
        self.assertEqual(membs.count(), 1)
        membership = membs.get()
        self.assertEqual(membership.state, ProjectMembership.ACCEPTED)

        user_quotas = quotas.get_users_quotas([self.member]).get(
            self.member.uuid).get(app1.chain.uuid)
        resource = 'service1.resource'
        newlimit = user_quotas[resource]['limit']
        self.assertEqual(newlimit, 10)

        remove_member_url = reverse('project_remove_member',
                                    kwargs={
                                        'project_uuid': app1.chain.uuid,
                                        'memb_id': membership.id
                                    })
        r = self.user_client.post(remove_member_url, follow=True)
        self.assertEqual(r.status_code, 200)

        user_quotas = quotas.get_users_quotas([self.member]).get(
            self.member.uuid).get(app1.chain.uuid)
        resource = 'service1.resource'
        newlimit = user_quotas[resource]['limit']
        self.assertEqual(newlimit, 0)

        # TODO: handy to be here, but should be moved to a separate test method
        # support email gets rendered in emails content
        for mail in get_mailbox('user@synnefo.org'):
            self.assertTrue(settings.CONTACT_EMAIL in
                            mail.message().as_string())
