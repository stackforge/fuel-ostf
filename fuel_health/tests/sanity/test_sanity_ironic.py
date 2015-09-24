# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import logging
import time
import traceback

from fuel_health.common.ssh import Client as SSHClient
from fuel_health import exceptions
from fuel_health import nmanager

LOG = logging.getLogger(__name__)


class SanityIronicTest(nmanager.SanityChecksTest):
    """TestClass contains tests that check the Ironic service availability
    Special requirements:
        1. A controller's IP address should be specified.
        2. A ironic-conductor's IP address should be specified.
        3. SSH user credentials for the controller and the ironic-conductor
           should be specified in the controller_node_ssh_user parameter
    """

    @classmethod
    def setUpClass(cls):
        super(SanityIronicTest, cls).setUpClass()
        cls.controllers = cls.config.compute.online_controllers
        cls.computes = cls.config.compute.online_computes
        cls.conductors = cls.config.ironic.online_conductors
        cls.usr = cls.config.compute.controller_node_ssh_user
        cls.pwd = cls.config.compute.controller_node_ssh_password
        cls.key = cls.config.compute.path_to_private_key
        cls.timeout = cls.config.compute.ssh_timeout
        cls.fuel_dns = cls.config.fuel.dns

    @classmethod
    def tearDownClass(cls):
        pass

    def test_001_ironic_services(self):
        """Check that Ironic services are running
        Target component: OpenStack Ironic

        Scenario:
            1. Execute pgrep -la ironic-api command on controller nodes.
            2. Check that ironic-api service is running.
            3. Execute pgrep -la ironic-conductor command on conductor nodes.
            4. Check that ironic-conductor service is running.
        Duration: 60 s.
        """
        # Step 1
        expected = u'/usr/bin/ironic-api'
        cmd = 'pgrep -la ironic-api'
        for controller in self.controllers:
            ssh_client = SSHClient(controller,
                                   self.usr, self.pwd,
                                   key_filename=self.key,
                                   timeout=self.timeout)
            output = self.verify(50, ssh_client.exec_command,
                                 1, "ironic-api service check failed. ",
                                 "ironic-api service check",
                                 cmd)
            LOG.debug(output)
            # Step 2
            try:
                self.verify_response_true(
                    expected in output, 'Step 2 failed: ironic-api '
                    'service not running.')
                break
            except exceptions.SSHExecCommandFailed:
                LOG.info("Will sleep for 60 seconds and try again.")
                LOG.debug(traceback.format_exc())
                time.sleep(60)
                self.verify_response_true(
                    expected in output, 'Step 2 failed: ironic-api '
                    'service not running.')

        # Step 3
        expected = u'/usr/bin/ironic-conductor'
        cmd = 'pgrep -la ironic'
        for conductor in self.conductors:
            ssh_client = SSHClient(conductor,
                                   self.usr, self.pwd,
                                   key_filename=self.key,
                                   timeout=self.timeout)
            output = self.verify(50, ssh_client.exec_command,
                                 3, "ironic-conductor service check failed. ",
                                 "ironic-conductor service check",
                                 cmd)
            LOG.debug(output)
            # Step 4
            try:
                self.verify_response_true(
                    expected in output, 'Step 4 failed: ironic-conductor '
                    'service not running.')
                break
            except exceptions.SSHExecCommandFailed:
                LOG.info("Will sleep for 60 seconds and try again")
                LOG.debug(traceback.format_exc())
                time.sleep(60)
                self.verify_response_true(
                    expected in output, 'Step 4 failed: ironic-conductor '
                    'service not running.')

    def test_002_ironic_node_actions(self):
        """Check that Ironic can operate nodes
        Target component: OpenStack Ironic

        Scenario:
            1. Create Ironic node with fake driver.
            2. Update ironic node properties.
            3. Check ironic node properties.
            4. Delete Ironic node.
        Duration: 60 s.
        """
        # Step 1
        cmd = 'source openrc && ironic node-create -d fake -n ironicnode'
        ssh_client = SSHClient(self.controllers[0],
                               self.usr, self.pwd,
                               key_filename=self.key,
                               timeout=self.timeout)
        output = self.verify(50, ssh_client.exec_command,
                             1, "ironic node creation failed. ",
                             "ironic node creation check",
                             cmd)
        LOG.debug(output)
        # Step 2
        expected = "{u'prop1': u'A', u'prop2': u'B'}"
        cmd = 'source openrc && ironic node-update ironicnode ' \
              'add properties/prop1=A properties/prop2=B'
        ssh_client = SSHClient(self.controllers[0],
                               self.usr, self.pwd,
                               key_filename=self.key,
                               timeout=self.timeout)
        output = self.verify(50, ssh_client.exec_command,
                             2, "ironic node update failed. ",
                             "ironic node update check",
                             cmd)
        LOG.debug(output)
        try:
            self.verify_response_true(
                expected in output, 'Step 2 failed: ironic node properties '
                'are not updated.')
        except exceptions.SSHExecCommandFailed:
            LOG.info("Will sleep for 60 seconds and try again")
            LOG.debug(traceback.format_exc())
            time.sleep(60)
            self.verify_response_true(
                expected in output, 'Step 2 failed: ironic node properties '
                'are not updated.')

        # Step 3
        cmd = 'source openrc && ironic node-show ironicnode'
        output = self.verify(50, ssh_client.exec_command,
                             2, "ironic node properties check failed. ",
                             "ironic node properties check",
                             cmd)
        LOG.debug(output)
        try:
            self.verify_response_true(
                expected in output, 'Step 2 failed: ironic node properties '
                'check failed.')
        except exceptions.SSHExecCommandFailed:
            LOG.info("Will sleep for 60 seconds and try again")
            LOG.debug(traceback.format_exc())
            time.sleep(60)
            self.verify_response_true(
                expected in output, 'Step 2 failed: ironic node properties '
                'check failed.')
        # Step 4
        expected = u'Deleted node ironicnode'
        cmd = 'source openrc && ironic node-delete ironicnode'
        ssh_client = SSHClient(self.controllers[0],
                               self.usr, self.pwd,
                               key_filename=self.key,
                               timeout=self.timeout)
        output = self.verify(50, ssh_client.exec_command,
                             3, "ironic node update failed. ",
                             "ironic node update check",
                             cmd)
        LOG.debug(output)
        try:
            self.verify_response_true(
                expected in output,
                'Step 3 failed: could not to delete ironic node')
        except exceptions.SSHExecCommandFailed:
            LOG.info("Will sleep for 60 seconds and try again")
            LOG.debug(traceback.format_exc())
            time.sleep(60)
            self.verify_response_true(
                expected in output, 'Step 3 failed: could not to delete '
                'ironic node.')
