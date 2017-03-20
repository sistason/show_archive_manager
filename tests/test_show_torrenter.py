#!/usr/bin/env python3

import unittest

from hamcrest import *
from tests.test_mocks import INFORMATION_MOCK, STATUS2TORRENT_MOCK


class ShowTorrenterTester(unittest.TestCase):
    def setUp(self):
        self._class = STATUS2TORRENT_MOCK

    def test_get_torrent(self):
        torrents = self._class.get_torrents(INFORMATION_MOCK)
        assert_that(len(torrents), equal_to(1))
        assert_that(torrents[0].links, equal_to(INFORMATION_MOCK.torrents[0].links))
        self._class.torrent_grabber.event_loop.close()

    def test_init(self):
        assert_that(self._class.torrent_grabber, is_not(None))

    def tearDown(self):
        self._class.close()
