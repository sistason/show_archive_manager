import json
from unittest.mock import MagicMock

from manager import Information
from a_argument_to_show.thetvdb_api import TheTVDBAPI, TVDBShow, Episode
from b_show_to_status.show_status import Status
from c_status_to_torrent.status2torrent import Status2Torrent, Torrent
from c_status_to_torrent.piratebay import PirateBayParser

from tests.test_mocks_data import EPISODE_DATA_MOCK, SHOWS_DATA_MOCK, PIRATEBAY_RESPONSE_SHORTENED

SHOWS_DATA_MOCK = SHOWS_DATA_MOCK.replace('\n', '')
SHOW_DATA_JSON_MOCK = json.loads(SHOWS_DATA_MOCK).get('data')[0]

SINGLE_EPISODE_DATA_MOCK = {'airedSeason': '2', 'airedEpisodeNumber': '13', 'episodeName': 'That One Episode',
                            'firstAired': '1970-2-1', 'absoluteNumber': '1337'}
SINGLE_TVDBSHOW_MOCK = {'seriesName': 'Supergirl', 'id': '295759', 'firstAired': '1970-1-1'}

INFORMATION_MOCK = Information('')
TheTVDBAPI_MOCK = TheTVDBAPI(test=True)
request_response_mock = MagicMock(ok=True, text=SHOWS_DATA_MOCK)
TheTVDBAPI_MOCK._make_request = MagicMock(return_value=request_response_mock)
TheTVDBAPI_MOCK.get_episode_data = MagicMock(return_value=EPISODE_DATA_MOCK)
TheTVDBAPI_MOCK.get_imdb_id_from_tvdb_id = MagicMock(return_value='tt4016454')

TVDB_SHOW_MOCK = TVDBShow(SHOW_DATA_JSON_MOCK, TheTVDBAPI_MOCK)
TVDB_SHOW_MOCK.fill_data()
SINGLE_EPISODE_MOCK = Episode(TVDB_SHOW_MOCK, SINGLE_EPISODE_DATA_MOCK)
INFORMATION_MOCK.show = TVDB_SHOW_MOCK

SHOW_STATUS_MOCK = Status([], [SINGLE_EPISODE_MOCK])
INFORMATION_MOCK.status = SHOW_STATUS_MOCK

STATUS2TORRENT_MOCK = Status2Torrent({'quality': '480p', 'encoder': 'x264'}, update_missing=True)

piratebay_parser = PirateBayParser()
PIRATEBAY_RESULTS = piratebay_parser.parse_piratebay_response(PIRATEBAY_RESPONSE_SHORTENED)
filtered = STATUS2TORRENT_MOCK.filter_searches(PIRATEBAY_RESULTS, SINGLE_EPISODE_MOCK)
sorted_ = STATUS2TORRENT_MOCK.sort_results(filtered)
TORRENT = Torrent(SINGLE_EPISODE_MOCK, sorted_)
INFORMATION_MOCK.torrents = [TORRENT]
