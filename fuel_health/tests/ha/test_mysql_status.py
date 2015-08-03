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

from fuel_health.common.ssh import Client as SSHClient
import fuel_health.test

LOG = logging.getLogger(__name__)


class TestMysqlStatus(fuel_health.test.BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestMysqlStatus, cls).setUpClass()
        cls.nodes = cls.config.compute.nodes
        cls.controller_ip = cls.config.compute.online_controllers[0]
        cls.node_key = cls.config.compute.path_to_private_key
        cls.node_user = cls.config.compute.ssh_user
        cls.mysql_user = 'root'
        cls.master_ip = []

        # retrieve data from controller
        ssh_client = SSHClient(
            cls.controller_ip, cls.node_user,
            key_filename=cls.node_key, timeout=100)
        hiera_cmd = 'ruby -e \'require "hiera"; ' \
                    'puts Hiera.new().lookup("database_nodes", {}, {}).keys\''
        database_nodes = ssh_client.exec_command(hiera_cmd)
        database_nodes = database_nodes.splitlines()

        # get online nodes
        cls.databases = []
        for node in cls.nodes:
            hostname = node['hostname']
            if hostname in database_nodes and node['online']:
                cls.databases.append(hostname)

    def setUp(self):
        super(TestMysqlStatus, self).setUp()
        if 'ha' not in self.config.compute.deployment_mode:
            self.skipTest('Cluster is not HA mode, skipping tests')
        if len(self.databases) == 1:
            self.skipTest('There is only one database online. '
                          'Nothing to check')

    def test_os_databases(self):
        """Check if amount of tables in databases is the same on each node
        Target Service: HA mysql

        Scenario:
            1. Request list of tables for os databases on each node.
            2. Check if amount of tables in databases is the same on each node
        Duration: 10 s.
        """
        LOG.info("'Test OS Databases' started")
        dbs = ['nova', 'glance', 'keystone']
        cmd = "mysql -h localhost -e 'SHOW TABLES FROM %(database)s'"
        for database in dbs:
            LOG.info('Current database name is %s' % database)
            temp_set = set()
            for node in self.databases:
                LOG.info('Current database node is %s' % node)
                cmd1 = cmd % {'database': database}
                LOG.info('Try to execute command %s' % cmd1)
                tables = SSHClient(
                    node, self.node_user,
                    key_filename=self.node_key,
                    timeout=self.config.compute.ssh_timeout)
                output = self.verify(40, tables.exec_command, 1,
                                     'Can list tables',
                                     'get amount of tables for each database',
                                     cmd1)
                tables = set(output.splitlines())
                if len(temp_set) == 0:
                    temp_set = tables
                self.verify_response_true(
                    len(tables.symmetric_difference(temp_set)) == 0,
                    "Step 2 failed: Tables in %s database are "
                    "different" % database)

            del temp_set

    @staticmethod
    def get_variables_from_output(output, variables):
        """Return dict with variables and their values extracted from mysql
        Assume that output is "| Var_name | Value |"
        """
        result = {}
        LOG.debug('Expected variables: "{0}"'.format(str(variables)))
        for line in output:
            try:
                var, value = line.strip("| ").split("|")[:2]
            except ValueError:
                continue
            var = var.strip()
            if var in variables:
                result[var] = value.strip()
        LOG.debug('Extracted values: "{0}"'.format(str(result)))
        return result

    def test_state_of_galera_cluster(self):
        """Check galera environment state
        Target Service: HA mysql

        Scenario:
            1. Ssh on each node contains database and request state of galera
               node
            2. For each node check cluster size
            3. For each node check status is ready
            4. For each node check that node is connected to cluster
        Duration: 10 s.
        """
        for db_node in self.databases:
            command = "mysql -h localhost -e \"SHOW STATUS LIKE 'wsrep_%'\""
            ssh_client = SSHClient(db_node, self.node_user,
                                   key_filename=self.node_key,
                                   timeout=100)
            output = self.verify(
                20, ssh_client.exec_command, 1,
                "Verification of galera cluster node status failed",
                'get status from galera node',
                command).splitlines()

            LOG.debug('mysql output from node "{0}" is \n"{1}"'.format(
                db_node, output)
            )

            mysql_vars = [
                'wsrep_cluster_size',
                'wsrep_ready',
                'wsrep_connected'
            ]
            result = self.get_variables_from_output(output, mysql_vars)

            self.verify_response_body_content(
                result.get('wsrep_cluster_size', 0),
                str(len(self.databases)),
                msg='Cluster size on %s less '
                    'than databases count' % db_node,
                failed_step='2')

            self.verify_response_body_content(
                result.get('wsrep_ready', 'OFF'), 'ON',
                msg='wsrep_ready on %s is not ON' % db_node,
                failed_step='3')

            self.verify_response_body_content(
                result.get('wsrep_connected', 'OFF'), 'ON',
                msg='wsrep_connected on %s is not ON' % db_node,
                failed_step='3')
