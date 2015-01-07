# -*- coding: utf-8 -*-

#    Copyright 2013 Mirantis, Inc.
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


import mock
import requests_mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import unittest2

from fuel_plugin.ostf_adapter import config
from fuel_plugin.ostf_adapter import mixins
from fuel_plugin.ostf_adapter.nose_plugin.nose_discovery import discovery
from fuel_plugin.ostf_adapter.storage import models


TEST_PATH = 'fuel_plugin/testing/fixture/dummy_tests'


CLUSTERS = {
    1: {
        'cluster_meta': {
            'release_id': 1,
            'mode': 'ha'
        },
        'release_data': {
            'operating_system': 'rhel'
        },
        'cluster_attributes': {
            'editable': {
                'additional_components': {},
                'common': {}
            }
        }
    },
    2: {
        'cluster_meta': {
            'release_id': 2,
            'mode': 'multinode',
        },
        'release_data': {
            'operating_system': 'ubuntu'
        },
        'cluster_attributes': {
            'editable': {
                'additional_components': {},
                'common': {}
            }
        }
    },
    3: {
        'cluster_meta': {
            'release_id': 3,
            'mode': 'ha'
        },
        'release_data': {
            'operating_system': 'rhel'
        },
        'cluster_attributes': {
            'editable': {
                'additional_components': {
                    'murano': {
                        'value': True
                    },
                    'sahara': {
                        'value': False
                    }
                },
                'common': {}
            }
        }
    },
    4: {
        'cluster_meta': {
            'release_id': 4,
            'mode': 'test_error'
        },
        'release_data': {
            'operating_system': 'none'
        },
        'cluster_attributes': {
            'editable': {
                'additional_components': {},
                'common': {}
            }
        }
    },
    5: {
        'cluster_meta': {
            'release_id': 5,
            'mode': 'dependent_tests'
        },
        'release_data': {
            'operating_system': 'none'
        },
        'cluster_attributes': {
            'editable': {
                'additional_components': {},
                'common': {}
            }
        }
    }
}


class BaseUnitTest(unittest2.TestCase):
    """Base class for all unit tests."""


class BaseIntegrationTest(BaseUnitTest):
    """Base class for all integration tests."""

    @classmethod
    def setUpClass(cls):
        config.init_config([])
        # db connection
        cls.dbpath = config.cfg.CONF.adapter.dbpath
        cls.Session = sessionmaker()
        cls.engine = create_engine(cls.dbpath)

        # mock http requests
        cls.requests_mock = requests_mock.Mocker()
        cls.requests_mock.start()

    @classmethod
    def tearDownClass(cls):
        # stop https requests mocking
        cls.requests_mock.stop()

    def setUp(self):
        # orm session wrapping
        self.connection = self.engine.connect()
        self.trans = self.connection.begin()

        self.Session.configure(
            bind=self.connection
        )
        self.session = self.Session()

    def tearDown(self):
        # rollback changes to database
        # made by tests
        self.trans.rollback()
        self.session.close()
        self.connection.close()

    def mock_api_for_cluster(self, cluster_id):
        """Mock requests to Nailgun to mimic behavior of
        Nailgun's API
        """
        cluster = CLUSTERS[cluster_id]
        release_id = cluster['cluster_meta']['release_id']

        self.requests_mock.register_uri(
            'GET',
            '/api/clusters/{0}'.format(cluster_id),
            json=cluster['cluster_meta'])

        self.requests_mock.register_uri(
            'GET',
            '/api/releases/{0}'.format(release_id),
            json=cluster['release_data'])

        self.requests_mock.register_uri(
            'GET',
            '/api/clusters/{0}/attributes'.format(cluster_id),
            json=cluster['cluster_attributes'])


class BaseWSGITest(BaseIntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(BaseWSGITest, cls).setUpClass()
        cls.ext_id = 'fuel_plugin.testing.fixture.dummy_tests.'
        cls.expected = {
            'cluster': {
                'id': 1,
                'deployment_tags': set(['ha', 'rhel', 'nova_network',
                                        'public_on_all_nodes'])
            },
            'test_sets': ['general_test',
                          'stopped_test', 'ha_deployment_test',
                          'environment_variables'],
            'tests': [cls.ext_id + test for test in [
                ('deployment_types_tests.ha_deployment_test.'
                 'HATest.test_ha_depl'),
                ('deployment_types_tests.ha_deployment_test.'
                 'HATest.test_ha_rhel_depl'),
                'general_test.Dummy_test.test_fast_pass',
                'general_test.Dummy_test.test_long_pass',
                'general_test.Dummy_test.test_fast_fail',
                'general_test.Dummy_test.test_fast_error',
                'general_test.Dummy_test.test_fail_with_step',
                'general_test.Dummy_test.test_skip',
                'general_test.Dummy_test.test_skip_directly',
                'stopped_test.dummy_tests_stopped.test_really_long',
                'stopped_test.dummy_tests_stopped.test_one_no_so_long',
                'stopped_test.dummy_tests_stopped.test_not_long_at_all',
                ('test_environment_variables.TestEnvVariables.'
                 'test_os_credentials_env_variables')
            ]]
        }

    def setUp(self):
        super(BaseWSGITest, self).setUp()
        test_sets = self.session.query(models.TestSet).all()

        # need this if start unit tests in conjuction with integration
        if not test_sets:
            discovery(path=TEST_PATH, session=self.session)

        mixins.cache_test_repository(self.session)

        # mocking
        # request mocking
        self.request_mock = mock.MagicMock()

        self.request_patcher = mock.patch(
            'fuel_plugin.ostf_adapter.wsgi.controllers.request',
            self.request_mock
        )
        self.request_patcher.start()

        # engine.get_session mocking
        self.request_mock.session = self.session

    def tearDown(self):
        super(BaseWSGITest, self).tearDown()

        # end of test_case patching
        self.request_patcher.stop()

        # clear "cache"
        mixins.TEST_REPOSITORY = []

    @property
    def is_background_working(self):
        is_working = True

        cluster_state = self.session.query(models.ClusterState)\
            .filter_by(id=self.expected['cluster']['id'])\
            .one()
        is_working = is_working and set(cluster_state.deployment_tags) == \
            self.expected['cluster']['deployment_tags']

        cluster_testing_patterns = self.session\
            .query(models.ClusterTestingPattern)\
            .filter_by(cluster_id=self.expected['cluster']['id'])\
            .all()

        for testing_pattern in cluster_testing_patterns:
            is_working = is_working and \
                (testing_pattern.test_set_id in self.expected['test_sets'])

            is_working = is_working and set(testing_pattern.tests)\
                .issubset(set(self.expected['tests']))

        return is_working
