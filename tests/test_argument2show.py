#!/usr/bin/env python3

import unittest
import logging

from hamcrest import *
from argument_to_show import Argument2Show


class Argument2ShowTester(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(format='%(message)s',
                            level=logging.DEBUG)
        self._class = Argument2Show()

    def test_api_login(self):
        assert_that(self._class.tvdb_api.jwt_token, not_none())

    def test_fitting(self):
        result = self._class.argument2show('supernatural')
        assert_that(result, not_none())
        assert_that(result.imdb_id, equal_to('tt0460681'))

    def test_partial(self):
        result = self._class.argument2show('flash 2014')
        assert_that(result, not_none())
        assert_that(result.imdb_id, equal_to('tt3107288'))

    def test_not_existing(self):
        result = self._class.argument2show('NONEXISTENT SHOW')
        assert_that(result, equal_to(None))

    def test_specified_multiples(self):
        result = self._class.argument2show('doctor who 2009')
        assert_that(result, not_none())
        assert_that(result.imdb_id, equal_to('tt0436992'))

    def test_imdbid(self):
        result = self._class.argument2show('tt0460681')
        assert_that(result, not_none())
        assert_that(result.name, equal_to('Supernatural'))
        assert_that(result.imdb_id, equal_to('tt0460681'))

if __name__ == "__main__":
    unittest.main()