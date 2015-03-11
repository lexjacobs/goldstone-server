"""Keystone tasks."""
# Copyright 2014 - 2015 Solinea, Inc.
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
from __future__ import absolute_import

from goldstone.celery import app as celery_app
import logging
from .models import EndpointsData, RolesData, ServicesData, \
    TenantsData, UsersData
from goldstone.utils import get_cloud


@celery_app.task()
def time_token_post_api():
    """Call a token URL via http rather than the Python client, so we can get
    a full set of data for the record in the DB.

    This will make things easier to model.

    """
    from goldstone.apps.api_perf.utils import time_api_call
    import json

    # Get the system's sole OpenStack cloud record.
    cloud = get_cloud()
    os_user = cloud.openstack_username
    os_password = cloud.openstack_password
    url = cloud.openstack_auth_url + "/tokens"

    payload = {"auth": {"passwordCredentials": {"username": os_user,
                                                "password": os_password}}}
    headers = {'content-type': 'application/json'}

    return time_api_call('keystone',
                         url,
                         method='POST',
                         data=json.dumps(payload),
                         headers=headers)


def _update_keystone_records(rec_type, region, database, items):
    from datetime import datetime
    from goldstone.utils import to_es_date
    import pytz

    # image list is a generator, so we need to make it not sol lazy it...
    body = {"@timestamp": to_es_date(datetime.now(tz=pytz.utc)),
            "region": region,
            rec_type: [item.to_dict() for item in items]}
    try:
        database.post(body)
    except Exception:           # pylint: disable=W0703
        logging.exception("failed to index keystone %s", rec_type)


@celery_app.task()
def discover_keystone_topology():
    from goldstone.utils import get_keystone_client, \
        get_region_for_keystone_client

    # Get the system's sole OpenStack cloud.
    cloud = get_cloud()

    access = get_keystone_client(cloud.os_username,
                                 cloud.os_password,
                                 cloud.os_tenant_name,
                                 cloud.os_auth_url)

    client = access['client']
    reg = get_region_for_keystone_client(client)

    _update_keystone_records("endpoints",
                             reg,
                             EndpointsData(),
                             client.endpoints.list())
    _update_keystone_records("roles", reg, RolesData(), client.roles.list())
    _update_keystone_records("services",
                             reg,
                             ServicesData(),
                             client.services.list())
    _update_keystone_records("tenants",
                             reg,
                             TenantsData(),
                             client.tenants.list())
    _update_keystone_records("users", reg, UsersData(), client.users.list())
