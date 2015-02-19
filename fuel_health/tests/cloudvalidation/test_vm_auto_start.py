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


class VMBootTest(cloudvalidation.CloudValidationTest):
    """Cloud Validation Test class for VMs."""

    def _check_host_boot(self, host):
        """Test resume_guest_state_on_host_boot option on compute node.
            By default, this option is set to False.
        """

        err_msg = ''.join("'The option resume_guest_state_on_host_boot' ",
                          "is set to True at compute node {host}.").format(
                  host=host)

        cmd = ''.join('cat /etc/nova/nova.conf | ',
                      'grep resume_guests_state_on_host_boot | ',
                      'grep "^[^#]"')

        out, err = self.verify(5, self._run_ssh_cmd, 1, err_msg,
                               'check host boot option', host, cmd)

        self.verify_response_true((not len(out) and not len(err))
                                  or (u'True' not in out
                                  and u'True' not in err),
                                  err_msg, 1)

    def test_guests_state_on_host_boot(self):
        """Check: host boot configuration on compute nodes
        Target component: Nova

        Scenario:
            1. Check NTP configuration on compute nodes

        Duration: 20 s.
        """

        for host in self.computes:
            self._check_host_boot(host)
