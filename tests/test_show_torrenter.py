#!/usr/bin/env python3

import unittest

from hamcrest import *
from tests.test_mocks import SHOW_STATUS_MOCK, SHOW_DOWNLOAD_MOCK, STATUS2PIRATEBAY_MOCK


class ShowTorrenterTester(unittest.TestCase):
    def setUp(self):
        self._class = STATUS2PIRATEBAY_MOCK

    def test_get_torrent(self):
        show_download = self._class.get_torrent(SHOW_STATUS_MOCK)
        assert_that(show_download.torrents_behind[0].links, equal_to(SHOW_DOWNLOAD_MOCK.torrents_behind[0].links))
        assert_that(show_download.torrents_missing, equal_to([]))
