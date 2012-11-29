from commissioning.specificator import (
    Specificator, Integer, Text, ListOf
)


class Name(Text):
    def init(self):
        self.opts.update({'regex': "[\w.:]+", 'maxlen': 512})
Name = Name()


class Email(Text):
    def init(self):
        pattern = "[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
        self.opts.update({'regex': pattern, 'maxlen': 512})
Email = Email()


class Url(Text):
    def init(self):
        pattern = "(((f|ht){1}tp://)[-a-zA-Z0-9@:%_\+.~#?&//=]+)"
        self.opts.update({'regex': pattern, 'maxlen': 512})
Url = Url()


class Filepath(Text):
    def init(self):
        self.opts.update({'regex': "", 'maxlen': 512})
Filepath = Filepath()


class Nonnegative(Integer):
    def init(self):
        self.opts.update({'minimum': 0})
Nonnegative = Nonnegative()


class Boolean(Integer):
    def init(self):
        self.opts.update({'minimum': 0, 'maximum': 1})
Boolean = Boolean()


# class GroupKind(Integer):
#     def init(self):
#         self.opts.update({'minimum': 1, 'maximum': 5})
# GroupKind = GroupKind()

Timepoint = Text(classname='Timepoint', maxlen=24)


class AstakosAPI(Specificator):
    def create_users(
        self,
        users=ListOf(
            email=Email,
            first_name=Name,
            last_name=Name,
            is_active=Boolean,
            is_superuser=Boolean,
            affiliation=Name,
            password=Name,
            provider=Name,
            level=Nonnegative,
            invitations=Nonnegative,
            is_verified=Boolean,
            third_party_identifier=Name,
            email_verified=Boolean),
        policies=ListOf(resource=Name, supimit=Nonnegative),
        groups=ListOf(Name),
        permissions=ListOf(Name)
    ):
        rejected = ListOf(user=Email, reason=Text())
        return rejected

    def update_users(
        self,
        users=ListOf(
            pk=Nonnegative,
            renew_token=Boolean,
            data=ListOf(
                first_name=Name,
                last_name=Name,
                is_active=Boolean,
                is_superuser=Boolean,
                affiliation=Name,
                password=Name,
                provider=Name,
                level=Nonnegative,
                invitations=Nonnegative,
                is_verified=Boolean,
                third_party_identifier=Name,
                email_verified=Boolean
            )
        )
    ):
        rejected = ListOf(user_id=Nonnegative, reason=Text())
        return rejected

    def add_user_policies(
        self,
        pk=Nonnegative,
        update=Boolean,
        policies=ListOf(service=Name, resource=Name, upimit=Nonnegative)
    ):
        rejected = ListOf(resource=Name, reason=Text())
        return rejected

    def remove_user_policies(
        self,
        pk=Nonnegative,
        policies=ListOf(service=Name, resource=Name)
    ):
        rejected = ListOf(service=Name, resource=Name)
        return rejected

    def add_user_permissions(
        self,
        pk=Nonnegative,
        permissions=ListOf(permission=Name)
    ):
        rejected = ListOf(permission=Name)
        return rejected

    def remove_user_permissions(
        self,
        pk=Nonnegative,
        permissions=ListOf(permission=Name)
    ):
        rejected = ListOf(permission=Name)
        return rejected

    def invite_users(
        self,
        sender=Email,
        data=ListOf(email=Email, realname=Name)
    ):
        rejected = ListOf(receiver=Email)
        return rejected

    def list_users(
        self,
        filter=ListOf(id=Nonnegative)
    ):
        return ListOf(
            activation_sent=Timepoint,
            affiliation=Name,
            auth_token=Name,
            auth_token_created=Timepoint,
            auth_token_expires=Timepoint,
            date_joined=Timepoint,
            date_signed_terms=Timepoint,
            email=Email,
            email_verified=Boolean,
            first_name=Name,
            has_credits=Boolean,
            has_signed_terms=Boolean,
            id=Nonnegative,
            invitations=Nonnegative,
            invitations_sent=ListOf(
                code=Name,
                consumed=Boolean,
                created=Timepoint,
                id=Nonnegative,
                realname=Name,
                username=Email
            ),
            is_active=Boolean,
            is_staff=Boolean,
            is_superuser=Boolean,
            is_verified=Boolean,
            last_login=Timepoint,
            last_name=Name,
            level=Nonnegative,
            password=Name,
            provider=Name,
            third_party_identifier=Name,
            updated=Timepoint,
            user_permissions=ListOf(
                codename=Name,
                id=Nonnegative,
                name=Name
            ),
            username=Name,
            astakos_groups=ListOf(
                approval_date=Timepoint,
                creation_date=Timepoint,
                desc=Text(),
                max_participants=Nonnegative,
                expiration_date=Timepoint,
                group_ptr=Url,
                homepage=Url,
                id=Nonnegative,
                issue_date=Timepoint,
                kind=Name,
                moderation_enabled=Boolean,
                name=Name,
                #permissions=ListOf(),
                policy=ListOf(id=Nonnegative, name=Name)
            )
        )

    def get_user_status(
        self,
        user_id=Nonnegative
    ):
        return ListOf(
            name=Name,
            description=Text(),
            unit=Name,
            maxValue=Integer(),
            currValue=Integer()
        )

    def list_resources(self, filter=ListOf(id=Nonnegative)):
        return ListOf(
            desc=Text(),
            group=Name,
            id=Nonnegative,
            meta=ListOf(key=Name, value=Name),
            name=Name,
            service=Name,
            unit=Name
        )

    def add_services(
        self,
        services=ListOf(
            name=Name,
            url=Url,
            icon=Filepath,
            resources=ListOf(
                name=Name,
                desc=Text(),
                unit=Name,
                group=Name
            )
        )
    ):
        rejected = ListOf(service=Name)
        return rejected

    def update_services(
        self,
        services=ListOf(id=Nonnegative, url=Url, icon=Filepath)
    ):
        rejected = ListOf(service=Name)
        return rejected

    def remove_services(self, ids=ListOf(Nonnegative)):
        rejected = ListOf(service=Name)
        return rejected

    def add_resources(
        self,
        service_id=Nonnegative,
        update=Boolean,
        resources=ListOf(
            name=Name,
            resources=ListOf(
                name=Name,
                desc=Text(),
                unit=Name,
                group=Name)
        )
    ):
        rejected = ListOf(service=Name)
        return rejected

    def remove_resources(
        self,
        service_id=Nonnegative,
        ids=ListOf(Nonnegative)
    ):
        rejected = ListOf(Name)
        return rejected

    def create_groups(
        self,
        groups=ListOf(
            name=Name,
            kind=Name,
            homepage=Url,
            desc=Text(),
            policies=ListOf(resource=Name, upimit=Nonnegative),
            issue_date=Timepoint,
            expiration_date=Timepoint,
            moderation_enabled=Boolean,
            participants=Nonnegative,
            permissions=ListOf(permission=Name),
            members=ListOf(user=Email, is_approved=Boolean),
            owners=ListOf(user=Email)
        )
    ):
        rejected = ListOf(group=Name)
        return rejected

    def enable_groups(self, data=ListOf(group=Name)):
        rejected = ListOf(group=Name)
        return rejected

    def search_groups(self, key=Name):
        return ListOf(
            group=Name,
            kind=Nonnegative,
            homepage=Url,
            desc=Text(),
            creation_date=Timepoint,
            issue_date=Timepoint,
            expiration_date=Timepoint,
            moderation_enabled=Boolean,
            participants=Nonnegative,
            owner=ListOf(user=Email),
            policies=ListOf(resource=Name, upimit=Nonnegative),
            members=ListOf(user=Email, is_approved=Boolean)
        )

    def list_groups(self):
        return ListOf(
            group=Name,
            kind=Nonnegative,
            homepage=Url,
            desc=Text(),
            creation_date=Timepoint,
            issue_date=Timepoint,
            expiration_date=Timepoint,
            moderation_enabled=Boolean,
            participants=Nonnegative,
            owners=ListOf(user=Email),
            policies=ListOf(resource=Name, upimit=Nonnegative),
            members=ListOf(user=Email, is_approved=Boolean)
        )

    def add_owners(
        self,
        data=ListOf(group=Name, owners=ListOf(user=Email))
    ):
        rejected = ListOf(user=Email)
        return rejected

    def remove_owners(
        self,
        data=ListOf(group=Name, owners=ListOf(user=Email))
    ):
        rejected = ListOf(user=Email)
        return rejected

    def add_members(
        self,
        data=ListOf(group=Name, members=ListOf(user=Email))
    ):
        rejected = ListOf(user=Email)
        return rejected

    def remove_members(
        self,
        data=ListOf(group=Name, members=ListOf(user=Email))
    ):
        rejected = ListOf(user=Email)
        return rejected

    def add_policies(
        self,
        data=ListOf(group=Name, resource=Name, upimit=Nonnegative)
    ):
        rejected = ListOf(group=Name, resource=Name)
        return rejected

    def remove_group_policies(
        self,
        data=ListOf(group=Name, resource=Name, upimit=Nonnegative)
    ):
        rejected = ListOf(group=Name, resource=Name)
        return rejected

    def update_group_policies(
        self, data=ListOf(group=Name, resource=Name, upimit=Nonnegative)
    ):
        rejected = ListOf(group=Name, resource=Name)
        return rejected

    def approve_members(
        self,
        data=ListOf(group=Name, members=ListOf(user=Email))
    ):
        rejected = ListOf(user=Email)
        return rejected

    def disapprove_members(
        self,
        data=ListOf(group=Name, members=ListOf(user=Email))
    ):
        rejected = ListOf(user=Email)
        return rejected

    def add_group_permissions(
        self,
        data=ListOf(group=Name, permission=Name)
    ):
        rejected = ListOf(group=Name, permission=Name)
        return rejected

    def delete_group_permissions(
        self,
        data=ListOf(group=Name, permission=Name)
    ):
        rejected = ListOf(group=Name, permission=Name)
        return rejected

    def list_resource_units(self):
        return ListOf(Name)

    def get_approval_terms(self, term=Nonnegative):
        return Text()

    def add_approval_terms(self, location=Filepath):
        return Nonnegative

#     def change_emails():
#         pass
