
import json
import asyncio
from unittest.mock import MagicMock
from tests.test_mocks_data import EPISODE_DATA_MOCK, SHOWS_DATA_MOCK, PIRATEBAY_RESPONSE_SHORTENED, \
    PIRATEBAY_RESULT_DATA_MOCK

from thetvdb_api import TheTVDBAPI, TVDBShow, Episode
from show_status import ShowStatus
from show_torrenter import ShowDownload, Status2Piratebay, Torrent, PirateBayResult


SHOWS_DATA_MOCK = SHOWS_DATA_MOCK.replace('\n', '')
SHOW_DATA_JSON_MOCK = json.loads(SHOWS_DATA_MOCK).get('data')[0]

SINGLE_EPISODE_DATA_MOCK = {'airedSeason': '2', 'airedEpisodeNumber': '13', 'episodeName': 'That One Episode',
                            'firstAired': '1970-2-1', 'absoluteNumber': '1337'}
SINGLE_TVDBSHOW_MOCK = {'seriesName': 'Supergirl', 'id': '295759', 'firstAired': '1970-1-1'}

TheTVDBAPI_MOCK = TheTVDBAPI(test=True)
request_response_mock = MagicMock(ok=True, text=SHOWS_DATA_MOCK)
TheTVDBAPI_MOCK._make_request = MagicMock(return_value=request_response_mock)
TheTVDBAPI_MOCK.get_episode_data = MagicMock(return_value=EPISODE_DATA_MOCK)
TheTVDBAPI_MOCK.get_imdb_id_from_tvdb_id = MagicMock(return_value='tt4016454')

TVDB_SHOW_MOCK = TVDBShow(SHOW_DATA_JSON_MOCK, TheTVDBAPI_MOCK)
TVDB_SHOW_MOCK.fill_data()
SINGLE_EPISODE_MOCK = Episode(TVDB_SHOW_MOCK, SINGLE_EPISODE_DATA_MOCK)

SHOW_STATUS_MOCK = ShowStatus(TVDB_SHOW_MOCK, '/tmp')
SHOW_STATUS_MOCK.episodes_missing = []
SHOW_STATUS_MOCK.episodes_behind = [SINGLE_EPISODE_MOCK]

STATUS2PIRATEBAY_MOCK = Status2Piratebay({'quality': '720p', 'encoder': 'x264'}, asyncio.get_event_loop(),
                                         update_missing=True)
request_response_mock = MagicMock(ok=True, text=PIRATEBAY_RESPONSE_SHORTENED)
STATUS2PIRATEBAY_MOCK._make_request = MagicMock(return_value=request_response_mock)

SHOW_DOWNLOAD_MOCK = ShowDownload(SHOW_STATUS_MOCK)
RESULT_MOCK = PirateBayResult(PIRATEBAY_RESULT_DATA_MOCK)
TORRENT_MOCK = Torrent(SINGLE_EPISODE_MOCK,
                       ["magnet:?xt=urn:btih:430ae2f38babd312fa535ef7f02c728318fe1782&dn=Supergirl.S02E13.HDTV.x264-LOL%5Bettv%5D&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fzer0day.ch%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fpublic.popcorn-tracker.org%3A6969"])
SHOW_DOWNLOAD_MOCK.torrents_behind = [TORRENT_MOCK]