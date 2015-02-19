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

from fuel_health import cloudvalidation

LOG = logging.getLogger(__name__)


class NTPTest(cloudvalidation.CloudValidationTest):
    """Cloud Validation Test class for NTP."""

    def _check_ntp(self, host, step, kind='unknown'):
        """Checks NTP on host."""

        err_msg = 'NTP is not configured on {kind} node {host}'.format(
                  kind=kind,
                  host=host)

        cmd = "ntpq -np"

        out, err = self.verify(5,
                               self._run_ssh_cmd,
                               step,
                               err_msg,
                               'check NTP',
                               host,
                               cmd)

        self.verify_response_true(u'Connection refused' not in err and
                                  u'Connection refused' not in out and
                                  u'No association ID' not in err and
                                  u'No association ID' not in out,
                                  err_msg,
                                  step)

    def test_ntp_on_nodes(self):
        """Test NTP on controller and compute nodes
        Target component: Nova

        Scenario:
            1. Check NTP configuration on controller nodes
            2. Check NTP configuration on compute nodes

        Duration: 20 s.
        """

        for host in self.controllers:
            self._check_ntp(host, 1, 'controller')

        for host in self.computes:
            self._check_ntp(host, 'compute')
