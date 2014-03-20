#    Copyright 2014 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import logging

from pecan import conf
from fuel_plugin.ostf_adapter.nose_plugin import nose_storage_plugin
from fuel_plugin.ostf_adapter.nose_plugin import nose_test_runner
from fuel_plugin.ostf_adapter.nose_plugin import nose_utils
from fuel_plugin.ostf_adapter.storage import engine, models


LOG = logging.getLogger(__name__)


class NoseDriver(object):
    def __init__(self):
        LOG.warning('Initializing Nose Driver')
        self._named_threads = {}

    def check_current_running(self, unique_id):
        return unique_id in self._named_threads

    def run(self, test_run, test_set, tests=None):
        tests = tests or test_run.enabled_tests
        if tests:
            argv_add = [nose_utils.modify_test_name_for_nose(test) for test in
                        tests]

        else:
            argv_add = [test_set.test_path] + test_set.additional_arguments

        self._named_threads[test_run.id] = nose_utils.run_proc(
            self._run_tests,
            conf.dbpath,
            test_run.id,
            test_run.cluster_id,
            argv_add
        )

    def _run_tests(self, dbpath, test_run_id, cluster_id, argv_add):
        with engine.contexted_session(dbpath) as session:
            try:
                nose_test_runner.SilentTestProgram(
                    addplugins=[nose_storage_plugin.StoragePlugin(
                        session, test_run_id, str(cluster_id))],
                    exit=False,
                    argv=['ostf_tests'] + argv_add)
                self._named_threads.pop(int(test_run_id), None)
            except Exception:
                LOG.exception('Test run ID: %s', test_run_id)
            finally:
                models.TestRun.update_test_run(
                    session, test_run_id, status='finished')

    def kill(self, session, test_run_id, cluster_id, cleanup=None):
        if test_run_id in self._named_threads:

            try:
                self._named_threads[test_run_id].terminate()
            except OSError as e:
                if e.errno != os.errno.ESRCH:
                    raise

                LOG.warning(
                    'There is no process for test_run with following id - %s',
                    test_run_id
                )

            self._named_threads.pop(test_run_id, None)

            if cleanup:
                nose_utils.run_proc(
                    self._clean_up,
                    conf.dbpath,
                    test_run_id,
                    cluster_id,
                    cleanup)
            else:
                models.TestRun.update_test_run(
                    session, test_run_id, status='finished')

            return True
        return False

    def _clean_up(self, dbpath, test_run_id, cluster_id, cleanup):
        with engine.contexted_session(dbpath) as session:
            #need for performing proper cleaning up for current cluster
            cluster_deployment_info = \
                session.query(models.ClusterState.deployment_tags)\
                .filter_by(id=cluster_id)\
                .scalar()

            try:
                module_obj = __import__(cleanup, -1)

                os.environ['NAILGUN_HOST'] = str(conf.nailgun.host)
                os.environ['NAILGUN_PORT'] = str(conf.nailgun.port)
                os.environ['CLUSTER_ID'] = str(cluster_id)

                module_obj.cleanup.cleanup(cluster_deployment_info)

            except Exception:
                LOG.exception(
                    'Cleanup error. Test Run ID %s. Cluster ID %s',
                    test_run_id,
                    cluster_id
                )

            finally:
                models.TestRun.update_test_run(
                    session, test_run_id, status='finished')
