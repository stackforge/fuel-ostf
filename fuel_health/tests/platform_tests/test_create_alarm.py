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
import traceback

from fuel_health import ceilometermanager
from fuel_health import nmanager

LOG = logging.getLogger(__name__)


class CeilometerApiSmokeTests(ceilometermanager.CeilometerBaseTest):
    """
    TestClass contains tests that check basic Ceilometer functionality.
    """

    def tearDown(self):
        super(CeilometerApiSmokeTests, self).tearDown()
        if self.alarm_list:
            for alarm in self.alarm_list:
                try:
                    self.ceilometer_client.alarms.delete(alarm.alarm_id)
                except:
                    LOG.warning('alarm deletion failed')
                    LOG.debug(traceback.format_exc())

    def test_create_alarm(self):
        """Ceilometer create, update, check, delete alarm.
        Target component: Ceilometer

        Scenario:
            1. Create metrics.
            2. Create a new alarm.
            3. List alarms
            4. Update the alarm.
            5. List statistic
            6. Get alarm history.
            7. Change alarm state to 'ok'.
            8. Verify state.
            9. List meters
            10. Delete the alarm.
        Duration: 700 s.
        Deployment tags: Ceilometer
        """

        fail_msg = "Creation metrics failed."

        self.verify(600, self.wait_for_instance_metrics, 1,
                    fail_msg,
                    "metrics created",
                    self.meter_name_image)

        fail_msg = "Creation alarm failed."

        create_alarm_resp = self.verify(100, self.create_alarm,
                                        2, fail_msg, "alarm_create",
                                        meter_name=self.meter_name,
                                        threshold=self.threshold,
                                        name=self.name,
                                        period=self.period,
                                        statistic=self.statistic,
                                        comparison_operator=self.comparison_operator)

        fail_msg = "Alarm list unavailable"

        self.verify(20, self.list_alarm,
                    2, fail_msg, "Alarm listing")

        fail_msg = "Alarm update failed."

        self.verify(20, self.alarm_update,
                    3, fail_msg, "Alarm_update",
                    alarm_id=create_alarm_resp.alarm_id,
                    threshold='50')

        fail_msg = "Alarm list unavailable"

        self.verify(20, self.list_statistics,
                    2, fail_msg, "Alarm listing",
                    meter_name=self.meter_name)

        fail_msg = "Get alarm history failed."

        self.verify(20, self.alarm_history,
                    4, fail_msg, "Alarm_history",
                    alarm_id=create_alarm_resp.alarm_id)

        fail_msg = "Alarm setting state failed."

        self.verify(20, self.set_state,
                    5, fail_msg, "Set_state",
                    alarm_id=create_alarm_resp.alarm_id,
                    state=self.state_ok)

        fail_msg = "Alarm verify state failed."

        self.verify(20, self.verify_state,
                    6, fail_msg, "Verify_state",
                    alarm_id=create_alarm_resp.alarm_id,
                    state=self.state_ok)

        fail_msg = "Meter list unavailable"

        self.verify(20, self.list_meters,
                    1, fail_msg, "Meter listing")

        fail_msg = "Alarm delete."
        self.verify(20, self.delete_alarm,
                    7, fail_msg, "Delete_alarm",
                    alarm_id=create_alarm_resp.alarm_id)

    def test_create_sample(self):
        """Create sample metric
        Target component: Ceilometer

        Scenario:
        1. Create sample for existing resource (the default image).
        2. Check that created sample has the expected resource.
        3. Check that the sample has the statistic.
        Duration: 40 s.
        Deployment tags: Ceilometer
        """

        fail_msg_1 = 'Sample can not be created'

        sample = self.verify(30, self.create_sample, 1,
                             fail_msg_1,
                             "Sample creating",
                             resource_id=nmanager.get_image_from_name(),
                             counter_name=self.counter_name,
                             counter_type=self.counter_type,
                             counter_unit=self.counter_unit,
                             counter_volume=self.counter_volume,
                             resource_metadata=self.resource_metadata)

        fail_msg_2 = 'Sample resource is absent'

        sample_resource = self.verify_response_body_value(
            body_structure=sample[0].resource_id,
            value=nmanager.get_image_from_name(),
            msg=fail_msg_2,
            failed_step=2)

        fail_msg_3 = 'Sample statistic list is unavailable.'

        sample_statistic = self.verify(5, self.list_statistics,
                                       3, fail_msg_3, "sample statistic",
                                       sample[0].counter_name)