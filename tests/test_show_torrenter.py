#!/usr/bin/env python3

import unittest

from hamcrest import *
from tests.test_mocks import SHOW_STATUS_MOCK, SHOW_DOWNLOAD_MOCK, STATUS2TORRENT_MOCK


class ShowTorrenterTester(unittest.TestCase):
    def setUp(self):
        self._class = STATUS2TORRENT_MOCK

    def test_get_torrent(self):
        show_download = self._class.get_torrents(SHOW_STATUS_MOCK)
        assert_that(len(show_download.torrents_behind), equal_to(1))
        assert_that(show_download.torrents_behind[0].links, equal_to(SHOW_DOWNLOAD_MOCK.torrents_behind[0].links))
        self._class.torrent_grabber.event_loop.close()

    def test_init(self):
        assert_that(self._class.torrent_grabber, is_not(None))

    def tearDown(self):
        self._class.close()
