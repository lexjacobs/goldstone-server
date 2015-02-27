"""Tenant views."""
# Copyright 2015 Solinea, Inc.
#
# Licensed under the Solinea Software License Agreement (goldstone),
# Version 1.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at:
#
#     http://www.solinea.com/goldstone/LICENSE.pdf
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from djoser.utils import SendEmailViewMixin
from rest_framework.permissions import BasePermission
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from goldstone.utils import django_admin_only
from goldstone.user.views import UserSerializer as AccountsUserSerializer
from .models import Tenant

logger = logging.getLogger(__name__)

# We need to get at the AccountsUserSerializer's fields property.  This appears
# to be the only way to do it. It's a hack.
HACK_OBJECT = AccountsUserSerializer()
HACK_FIELDS = HACK_OBJECT.fields.keys()


class UserSerializer(AccountsUserSerializer):
    """A User table serializer that's used when accessing a user as a "child"
    of his/her tenant. E.g., /tenants/<id>/user/<id>.

    This adds the Tenant relationship, and exposes more fields.

    """

    class Meta:          # pylint: disable=C1001,C0111,W0232
        model = get_user_model()
        fields = HACK_FIELDS + ["tenant"]


class TenantSerializer(ModelSerializer):

    """The Tenant model serializer."""

    class Meta:          # pylint: disable=C1001,C0111,W0232
        model = Tenant
        fields = ["name", "owner", "owner_contact", "uuid"]
        read_only_fields = ('uuid', )


class DjangoOrTenantAdminPermission(BasePermission):
    """A custom permissions class that allows access if the user is a Django
    Admin, or a tenant_admin for the Tenant row being accessed."""

    def has_object_permission(self, request, view, obj):
        """Override the permissions check for single Tenant row access.

        :return: True if the request should be granted, False otherwise
        :rtype: bool

        """

        user = request.user
        return user.is_staff or (user.tenant_admin and user.tenant == obj)


class BaseViewSet(NestedViewSetMixin, ModelViewSet):
    """A base class for this app's Tenant and User ViewSets."""

    lookup_field = "uuid"

    def get_object(self):
        """Return the desired object for this request.

        Because the API's selection string is a UUID, we have to
        do a little extra work to filter by UUID. Hence, we have to
        override get_object().

        """
        from uuid import UUID

        # Pad the UUID hexadecimal value, extracted from the request URL, to 32
        # hex digits. Then create a UUID object with it.
        value = UUID(hex=self.kwargs[self.lookup_field].zfill(32))

        # Return the object having this UUID.
        return self.get_queryset().get(**{self.lookup_field: value})


class TenantsViewSet(SendEmailViewMixin, BaseViewSet):
    """Provide all of the /tenants views."""

    serializer_class = TenantSerializer
    permission_classes = (DjangoOrTenantAdminPermission, )

    def get_email_context(self, user):
        """Replace the SendEmailViewMixin's e-mail sending method.

        When we send tenant_admins e-mail about their being added as an admin
        for a new tenant, this provides some context to the templates that are
        used.

        :param user: A tenant_admin user, with the additional attribute
                     perform_create_tenant_name
        :type user: User

        """
        from djoser import settings

        return {'domain': settings.get('DOMAIN'),
                'site_name': settings.get('SITE_NAME'),
                'protocol': 'https' if self.request.is_secure() else 'http',
                "tenant_name": user.perform_create_tenant_name
                }

    def get_send_email_extras(self):
        """Override djoser's SendEmailViewMixin method.

        At some point it'll be more sensible to just write code for sending an
        email rather than do all this subclassing.

        """

        return {'subject_template_name': 'new_tenant.txt',
                'plain_body_template_name': 'new_tenant_body.txt'}

    def get_queryset(self):

        """Return the queryset for list views."""

        return Tenant.objects.all()

    def get_object(self):
        """Return an object (e.g., for a detail view) iff (the user is a Django
        admin) or ((the request isn't a DELETE) and (the user is a tenant_admin
        of the tenant in question))."""

        try:
            tenant = super(TenantsViewSet, self).get_object()
        except ObjectDoesNotExist:
            raise PermissionDenied

        # N.B. user.is_authenticated() filters out the AnonymousUser object.
        if self.request.user.is_authenticated() and \
           (self.request.user.is_staff or
            (self.request.user.tenant == tenant and
             self.request.method != "DELETE")):
            return tenant
        else:
            raise PermissionDenied

    @django_admin_only
    def perform_create(self, serializer):
        """Add the system's default tenant_admin as the tenant_admin, and
        member, of the tenant we are creating.

        """

        # Do what the superclass' perform_create() does, to get the newly
        # created row.
        tenant = serializer.save()

        # Find the default tenant_admin. Use a filter in case there's
        # erroneously more than one in the system.
        admin_user = get_user_model().objects.filter(default_tenant_admin=True)

        if not admin_user:
            # There should always be a default tenant_admin.
            logger.warning("There are no default tenant_admins in the system."
                           " Using the Django administrator instead.")
            admin_user = self.request.user
        elif admin_user.count() > 1:
            # More than one default tenant_admin is odd, but we'll continue.
            logger.warning("The system has more then one default tenant admin."
                           " There should be only one: %s",
                           admin_user)
            admin_user = admin_user[0]
        else:
            # We found the single default tenant_admin.
            admin_user = admin_user[0]

        # Insert the default tenant_admin into the tenant and save it.
        admin_user.tenant_admin = True
        admin_user.tenant = tenant
        admin_user.save()

        # Notify the tenant_admin by e-mail that he/she's administering this
        # tenant. We tack the tenant's name to the User object so that our
        # overridden get_email_context can get at it.
        admin_user.perform_create_tenant_name = tenant.name
        self.send_email(**self.get_send_email_kwargs(admin_user))

    @django_admin_only
    def list(self, request, *args, **kwargs):
        """Provide a collection-of-objects GET response, for Django admins."""
        from rest_framework.response import Response

        # Return all the tenants to this Django admin.
        instance = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(instance)

        serializer = \
            self.get_serializer(instance, many=True) if page is None else \
            self.get_pagination_serializer(page)

        return Response(serializer.data)


class UserViewSet(BaseViewSet):
    """A ViewSet for the User table, which is used only in this app's
    "parent/child" views."""

    serializer_class = UserSerializer

    def _get_tenant(self):
        """Return the underlying Tenant row for this request, or raise a
        PermissionDenied exception."""

        target_uuid = self.get_parents_query_dict()["tenant"]

        try:
            return Tenant.objects.get(uuid=target_uuid)
        except ObjectDoesNotExist:
            raise PermissionDenied

    def get_queryset(self):
        """Return the queryset for list views iff the user is a tenant_admin of
        the underlying tenant."""

        # Get the underlying Tenant row for this request.
        tenant = self._get_tenant()

        # N.B. User.is_authenticated() filters out the AnonymousUser object.
        if self.request.user.is_authenticated() and \
           self.request.user.tenant == tenant and \
           self.request.user.tenant_admin:
            # We can't use filter_queryset_by_parents_lookup() here, because of
            # an interaction between Django's ORM and the UUID model. I think
            # the ORM doesn't invoke the __eq__ special method. So, we do
            # manual filtering.
            return [x for x in get_user_model().objects.all()
                    if x.tenant == tenant]
        else:
            raise PermissionDenied

    def perform_create(self, serializer):
        """Create a user for the underlying Tenant."""

        # Get the underlying Tenant row for this request.
        tenant = self._get_tenant()

        # N.B. User.is_authenticated() filters out the AnonymousUser object.
        if self.request.user.is_authenticated() and \
           self.request.user.tenant == tenant:
            # We are clear to create a new user, as a member of this tenant.
            # Do what the superclass' perform_create() does, to get the newly
            # created row.
            user = serializer.save()

            # # Notify the tenant_admin by e-mail that he/she's administering this
            # # tenant. We tack the tenant's name to the User object so that our
            # # overridden get_email_context can get at it.
            # admin_user.perform_create_tenant_name = tenant.name
            # self.send_email(**self.get_send_email_kwargs(admin_user))

        else:
            raise PermissionDenied
