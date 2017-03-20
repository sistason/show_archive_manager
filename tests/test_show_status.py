#!/usr/bin/env python3

import os
import shutil
import tempfile
import unittest

from hamcrest import *
from b_show_to_status.show2status import Show2Status
from tests.test_mocks import SHOW_DATA_JSON_MOCK, INFORMATION_MOCK


class ShowStatusTester(unittest.TestCase):
    def setUp(self):
        self.temp_path = os.path.join('/tmp/', SHOW_DATA_JSON_MOCK.get('seriesName'))

        os.makedirs(os.path.join(self.temp_path, 'Season 1'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_path, 'Season 2'), exist_ok=True)
        self.tempepisodes = [tempfile.NamedTemporaryFile(dir=os.path.join(self.temp_path, 'Season 2'), delete=True,
                                                         prefix='{} s02e{:02} '.format(
                                                             SHOW_DATA_JSON_MOCK.get('seriesName'), i))
                             for i in range(1, 10)]

        self._class = Show2Status(True)
        self.temp_dir_info_mock = INFORMATION_MOCK
        self.temp_dir_info_mock.download_directory = '/tmp'
        self._status = self._class.analyse(self.temp_dir_info_mock)

    def test_episode_holes(self):
        assert_that(len(self._status.episodes_missing), equal_to(20))

    def test_episode_behind(self):
        assert_that(len(self._status.episodes_behind), equal_to(7))

    def tearDown(self):
        [t.close() for t in self.tempepisodes]
        shutil.rmtree(self.temp_path, ignore_errors=True)

