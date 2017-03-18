#!/usr/bin/env python3

import unittest
import asyncio

from hamcrest import *
from tests.test_mocks import SHOW_STATUS_MOCK, SHOW_DOWNLOAD_MOCK, STATUS2PIRATEBAY_MOCK, RESULT_MOCK
from show_torrenter import Result


class ShowTorrenterTester(unittest.TestCase):
    def setUp(self):
        self._class = STATUS2PIRATEBAY_MOCK

    @unittest.SkipTest
    def test_get_torrent(self):
        # Asyncronous Mocks are not yet a thing :(
        future = asyncio.ensure_future(self._class.get_torrents(SHOW_STATUS_MOCK))
        self._class.event_loop.run_until_complete(future)
        show_download = future.result()
        assert_that(show_download.torrents_behind[0].links, equal_to(SHOW_DOWNLOAD_MOCK.torrents_behind[0].links))
        assert_that(show_download.torrents_missing, equal_to([]))

    @staticmethod
    def test_compare():
        unsorted = [Result(), RESULT_MOCK]
        assert_that(sorted(unsorted), is_not(unsorted))
