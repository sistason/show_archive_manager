#!/usr/bin/env python3

import unittest
import os
import shutil
import tempfile

from hamcrest import *
from tests.test_mocks import SHOW_DATA_JSON_MOCK, TVDB_SHOW_MOCK
from show_status import ShowStatus


class ShowStatusTester(unittest.TestCase):
    def setUp(self):
        self.temp_path = os.path.join('/tmp/', SHOW_DATA_JSON_MOCK.get('seriesName'))

        os.makedirs(os.path.join(self.temp_path, 'Season 1'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_path, 'Season 2'), exist_ok=True)
        self.tempepisodes = [tempfile.NamedTemporaryFile(dir=os.path.join(self.temp_path, 'Season 2'), delete=True,
                                                         prefix='{} s02e{:02} '.format(
                                                             SHOW_DATA_JSON_MOCK.get('seriesName'), i))
                             for i in range(1, 10)]

        self._class = ShowStatus(TVDB_SHOW_MOCK, '/tmp')
        self._class.analyse()

    def test_episode_holes(self):
        assert_that(len(self._class.episode_holes), equal_to(28))

    def test_episode_behind(self):
        assert_that(len(self._class.episodes_behind), equal_to(6))

    def tearDown(self):
        [t.close() for t in self.tempepisodes]
        shutil.rmtree(self.temp_path, ignore_errors=True)

