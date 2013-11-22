# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Mirantis, Inc.
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
from fuel_health import ceilometermanager

LOG = logging.getLogger(__name__)


class CeilometerApiTests(ceilometermanager.CeilometerBaseTest):
    """
    TestClass contains tests that check basic Ceilometer functionality.
    """

    def test_list_meters(self):
        """List Ceilometer availability
        Target component: Ceilometer

        Scenario:
            1. Request the list of meters
            2. Request the list of alarms
            3. Request the list of resources.

        Duration: 5 s.
        Deployment tags: Ceilometer
        """
        fail_msg = "Meter list unavailable"

        list_meters_resp = self.verify(20, self.list_meters,
                                       1, fail_msg, "Meter listing")

        fail_msg = "Alarm list unavailable"

        list_alarms_resp = self.verify(20, self.list_alarm,
                                       2, fail_msg, "Alarm listing")

        fail_msg = 'Resource list is unavailable. '

        list_resources_resp = self.verify(5, self.list_resources,
                                          3, fail_msg, "Resource listing")
