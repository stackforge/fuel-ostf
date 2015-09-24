# Copyright 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ironicclient
import logging

from fuel_health.common.utils.data_utils import rand_name
from fuel_health import ironicmanager

LOG = logging.getLogger(__name__)


class IronicSmokeTests(ironicmanager.IronicTest):
    """TestClass contains tests to check that Ironic nodes are operable"""

    @classmethod
    def setUpClass(cls):
        super(IronicSmokeTests, cls).setUpClass()
        cls.controllers = cls.config.compute.online_controllers
        cls.computes = cls.config.compute.online_computes
        cls.conductors = cls.config.ironic.online_conductors
        cls.usr = cls.config.compute.controller_node_ssh_user
        cls.pwd = cls.config.compute.controller_node_ssh_password
        cls.key = cls.config.compute.path_to_private_key
        cls.timeout = cls.config.compute.ssh_timeout
        cls.fuel_dns = cls.config.fuel.dns
        # setup ironicclient below
        super(IronicSmokeTests, cls).setUp()
        cls.client = ironicclient.client.get_client(**cls._get_config())

    @classmethod
    def tearDownClass(cls):
        pass

    def test_ironic_node_actions(self):
        """Check that Ironic can operate nodes
        Target component: OpenStack Ironic

        Scenario:
            1. Create Ironic node with fake driver.
            2. Update Ironic node properties.
            3. Verify Ironic node properties.
            4. Delete Ironic node.
        Duration: 60 s.
        """
        # Step 1
        fail_msg = ("Error creating node. Please refer to Openstack logs "
                    "for more information.")
        self.node = self.verify(100, self.node_create, 1, fail_msg,
                                'Node creation',
                                self.client, '-d fake', '-n ironicnode')
        # Step 2
        group_props = rand_name("ostf_test")
        prop = rand_name("ostf-prop")
        value_prop = rand_name("prop-value")

        fail_msg = ("Can't update node with properties. Please refer to "
                    "Openstack logs for more information.")
        # need method node_update in ironicmanager
        self.image = self.verify(100, self.node_update, 2, fail_msg,
                                 'Updating node', self.client,
                                 self.node, group_props, prop, value_prop)

        # Step 3
        fail_msg = ("Can't find appended properties. Please refer to "
                    "OSTF logs for more information.")
        # need method find_props in ironicmanager
        self.verify(100, self.find_props, 3, fail_msg, 'Finding properties',
                    self.client, self.node, group_props, prop,
                    value_prop)

        # Step 4
        fail_msg = ("Cant' delete node. Please refer to Openstack logs "
                    "for more information.")
        self.verify(100, self.delete_image, 4, fail_msg, 'Deleting node',
                    self.client, self.node)
