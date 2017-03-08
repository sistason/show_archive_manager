#!/usr/bin/env python3

import unittest
import os
import shutil
import tempfile

from hamcrest import *
from tests.test_mocks import SHOW_STATUS_MOCK, SHOW_DOWNLOAD_MOCK, STATUS2PIRATEBAY_MOCK
from show_torrenter import Status2Piratebay


class ShowTorrenterTester(unittest.TestCase):
    def setUp(self):
        self._class = STATUS2PIRATEBAY_MOCK

    def test_get_torrent(self):
        show_download = self._class.get_torrent(SHOW_STATUS_MOCK)
        assert_that(show_download.download_links_behind, equal_to(SHOW_DOWNLOAD_MOCK.download_links_behind))
        assert_that(show_download.download_links_missing, equal_to([]))