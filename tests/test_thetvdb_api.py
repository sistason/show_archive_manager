#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock
import datetime

from hamcrest import *
from thetvdb_api import TheTVDBAPI, TVDBShow, Season, Episode
from tests.test_mocks import SINGLE_EPISODE_MOCK, TheTVDBAPI_MOCK, SINGLE_TVDBSHOW_MOCK, \
    SINGLE_EPISODE_DATA_MOCK, TVDB_SHOW_MOCK


class TheTVDBAPITester(unittest.TestCase):
    def setUp(self):
        self._class = TheTVDBAPI_MOCK

    def test_total_by_imdb_id(self):
        supergirl_show = self._class.get_show_by_imdb_id('tt4016454')
        assert_that(supergirl_show, is_not(None))
        self._test_show_content(supergirl_show)

    def test_total_by_search(self):
        supergirl_show = self._class.get_shows_by_search('Supergirl', year=2015)
        assert_that(len(supergirl_show), equal_to(1))
        self._test_show_content(supergirl_show[0])

    @staticmethod
    def _test_show_content(supergirl_show):
        assert_that(supergirl_show.imdb_id, equal_to('tt4016454'))
        assert_that(supergirl_show.tvdb_id, equal_to(295759))
        assert_that(supergirl_show.name, equal_to('Supergirl'))
        assert_that(supergirl_show.aired.strftime('%s'), equal_to('1445814000'))
        assert_that(len(supergirl_show.seasons), equal_to(2))
        assert_that(len(supergirl_show.episodes), equal_to(37))


class TVDBShowTester(unittest.TestCase):
    def setUp(self):

        api_mock = TheTVDBAPI(test=True)
        api_mock.get_episode_data = MagicMock(return_value=[SINGLE_EPISODE_DATA_MOCK])
        api_mock.get_imdb_id_from_tvdb_id = MagicMock(return_value='tt4016454')

        self._class = TVDBShow(SINGLE_TVDBSHOW_MOCK, api_mock)

    def test_init(self):
        assert_that(len(self._class.seasons), equal_to(1))
        assert_that(list(self._class.seasons.keys()), equal_to([2]))
        assert_that(self._class.episodes, equal_to([SINGLE_EPISODE_MOCK]))
        assert_that(self._class.aired.strftime('%s'), equal_to('-3600'))
        assert_that(self._class.name, equal_to('Supergirl'))
        assert_that(self._class.tvdb_id, equal_to('295759'))
        assert_that(self._class.imdb_id, equal_to('tt4016454'))

    def test_episode_times(self):
        today = datetime.date.today()
        assert_that(self._class.get_newest_episode(), equal_to(self._class.episodes[0]))
        assert_that(self._class.get_episodes_since(self._class.aired), equal_to(self._class.episodes))

        new_episode = SINGLE_EPISODE_DATA_MOCK.copy()
        new_episode['firstAired'] = '1970-01-01'
        new_episode = Episode(self._class, new_episode)
        self._class._add_episode(new_episode)
        assert_that(self._class.get_newest_episode(), equal_to(self._class.episodes[0]))
        assert_that(self._class.get_episodes_since(today), equal_to([]))

        new_episode = SINGLE_EPISODE_DATA_MOCK.copy()
        new_episode['firstAired'] = '2001-05-06'
        new_episode = Episode(self._class, new_episode)
        self._class._add_episode(new_episode)
        assert_that(self._class.get_newest_episode(), equal_to(new_episode))
        assert_that(self._class.get_episodes_since(datetime.date(year=2000, month=1, day=1)), equal_to([new_episode]))

    def test_builtin(self):
        assert_that(str(self._class), equal_to('Supergirl [tt4016454]'))
        assert_that(bool(self._class), equal_to(True))


class SeasonTester(unittest.TestCase):
    def setUp(self):
        self.episode = SINGLE_EPISODE_MOCK
        self._class = Season(TVDB_SHOW_MOCK, self.episode)

    def test_init(self):
        assert_that(self._class.number, equal_to(2))
        assert_that(len(self._class.episodes), equal_to(1))

    def test_add_episode(self):
        assert_that(len(self._class.episodes), equal_to(1))
        self._class.add_episode(self.episode)
        assert_that(len(self._class.episodes), equal_to(1))
        episode = SINGLE_EPISODE_DATA_MOCK.copy()
        episode['absoluteNumber'] = 9001
        self._class.add_episode(Episode(TVDB_SHOW_MOCK, episode))
        assert_that(len(self._class.episodes), equal_to(2))

    def test_get_aired_episodes(self):
        assert_that(len(self._class.get_aired_episodes()), equal_to(1))

    def test_regex(self):
        assert_that(self._class.get_season_from_string("Season 800"), equal_to(800))
        assert_that(self._class.get_season_from_string("Season"), equal_to(0))
        assert_that(self._class.get_season_from_string(""), equal_to(0))
        assert_that(self._class.get_season_from_string("The Seasons"), equal_to(0))
        assert_that(self._class.get_season_from_string("Season Summer"), equal_to(0))

    def test_builtin(self):
        assert_that(str(self._class), equal_to("Season 2"))


class EpisodeTester(unittest.TestCase):
    def setUp(self):
        self._class = SINGLE_EPISODE_MOCK

    def test_init(self):
        assert_that(self._class.season, equal_to(2))
        assert_that(self._class.episode, equal_to(13))
        assert_that(self._class.name, equal_to('That One Episode'))
        assert_that(self._class.date.strftime('%s'), equal_to('2674800'))
        assert_that(self._class.absolute_episode_number, equal_to(1337))

    def test_init_wrong(self):
        _class = Episode(TVDB_SHOW_MOCK, {'airedSeason': None, 'episodeName': None})
        assert_that(_class.season, equal_to(0))
        assert_that(_class.episode, equal_to(0))
        assert_that(_class.name, equal_to(None))
        assert_that(_class.date.strftime('%s'), equal_to('-3600'))
        assert_that(_class.absolute_episode_number, equal_to(0))
        assert_that(_class, is_not(self._class))

    def test_regex(self):
        searches_ = ['Foo S02E13', 'Bar 2x13']
        for search_ in searches_:
            search_re = self._class.get_regex().search(search_)
            assert_that(search_re, not_none())
            assert_that(search_re.group('season'), equal_to('2'))
            assert_that(search_re.group('episode'), equal_to('13'))

        searches_wrong = ['Foo S02E14', 'Babylon 5.2 e14', 'Bar s02e131']
        for search_ in searches_wrong:
            assert_that(self._class.get_regex().search(search_), equal_to(None))

    def test_builtin(self):
        assert_that(str(self._class), equal_to('s02e13'))

    def test_logic(self):
        _class = Episode(TVDB_SHOW_MOCK, {'airedSeason': None, 'episodeName': None})
        assert_that(bool(self._class), is_(True))
        assert_that(bool(_class), is_(False))
