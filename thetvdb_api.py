import json
import time
import logging
import requests
import datetime


def get_airdate(data):
    try:
        return datetime.datetime.strptime(data.get('firstAired', '0-0-0'), '%Y-%m-%d').date()
    except ValueError:
        return datetime.datetime.fromtimestamp(0).date()


class TheTVDBAPI:
    API_KEY = "87EF0C7BB9CA4283"
    url = 'https://api.thetvdb.com/'

    def __init__(self):
        logging.getLogger("requests").setLevel(logging.WARNING)

        self.jwt_token = self.login()
        if not self.jwt_token:
            logging.error('Could not login to TheTVDB-API. Invalid API-Key?')

        self.headers = {'Accept-Language': 'en', 'Accept': 'application/json',
                        'Authorization': 'Bearer {}'.format(self.jwt_token)}

    def login(self):
        data = json.dumps({'apikey': self.API_KEY})
        ret = requests.post(self.url + "login", data=data, headers={'Content-Type': 'application/json'})
        if ret.ok:
            ret_j = json.loads(ret.text)
            return ret_j.get('token', None)

    def get_shows_by_search(self, search, year=None):
        url = self.url + 'search/series?name={}'.format(search)
        response = self._make_request(url)
        responses = self._validate_response_to_json(response)
        if year:
            responses = self._filter_search_by_year(responses, year)
        return [self._json_to_show(r) for r in responses]

    def get_show_by_imdb_id(self, imdb_id):
        response = self._make_request(self.url + 'search/series?imdbId={}'.format(imdb_id))
        responses = self._validate_response_to_json(response)
        return self._json_to_show(responses[0]) if responses else None

    def _json_to_show(self, response):
        return TVDBShow(response, self) if response else None

    @staticmethod
    def _filter_search_by_year(responses, year):
        return [r for r in responses if r.get('firstAired', '0-0-0').split('-')[0] == str(year)]

    @staticmethod
    def _validate_response_to_json(response):
        if response is not None and response.ok:
            ret_j = json.loads(response.text)
            return ret_j.get('data', [])
        return []

    def _make_request(self, url, data=None):
        """ Do a request, take care of timeouts and exceptions """
        if data is None:
            data = {}
        for _ in range(3):
            try:
                return requests.get(url, data=data, headers=self.headers, timeout=2)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                time.sleep(1)
            except Exception as e:
                logging.debug(
                    'Caught Exception "{}" while making a get-request to "{}"'.format(e.__class__, url))
                return

    def get_episode_data(self, tvdb_show):
        episodes_ = self._make_request(self.url + 'series/{}/episodes'.format(tvdb_show.tvdb_id))
        return self._validate_response_to_json(episodes_)

    def get_imdb_id_from_tvdb_id(self, tvdb_id):
        response = self._make_request(self.url + 'series/{}'.format(tvdb_id))
        response_j = self._validate_response_to_json(response)
        return response_j.get('imdbId', 'tt0')


class TVDBShow:
    def __init__(self, json_result, api_):
        self.raw = json_result
        self.api = api_

        self.aired = get_airdate(json_result)
        self.name = json_result.get('seriesName', '')
        self.tvdb_id = json_result.get('id', '0')
        self.imdb_id = api_.get_imdb_id_from_tvdb_id(self.tvdb_id)

        self.seasons = {}
        self.episodes = []
        for ep_j in api_.get_episode_data(self):
            self._add_episode(Episode(ep_j))

    def _add_episode(self, episode):
        if episode:
            self.episodes.append(episode)
            if episode.season in self.seasons.keys():
                self.seasons[episode.season].add_episode(episode)
            else:
                self.seasons[episode.season] = Season(episode)

    def get_newest_episode(self):
        today = datetime.date.today()
        episodes_ = [ep for ep in self.episodes if ep.date <= today]
        return max(episodes_, key=lambda ep: ep.date) if episodes_ else {}

    def __str__(self):
        return '{} [{}]'.format(self.name, self.imdb_id)


class Season:
    def __init__(self, init_episode):
        self.season = init_episode.season
        self.episodes = [init_episode]

    def add_episode(self, episode):
        if episode not in self.episodes:
            self.episodes.append(episode)


class Episode:
    def __init__(self, json_data):
        self.season = self._get_if_true(json_data, 'airedSeason', 0)
        self.episode = self._get_if_true(json_data, 'airedEpisodeNumber', 0)
        self.name = json_data.get('episodeName', '')
        self.date = get_airdate(json_data)
        self.absolute_episode_number = self._get_if_true(json_data, 'absoluteNumber', 0)

    @staticmethod
    def _get_if_true(data, value, default):
        item = data.get(value, default)
        return default if not item else item

    def __str__(self):
        return "s{s.season:02}e{s.episode:02}: {s.name} [{s.absolute_episode_number}]".format(s=self)

    def __bool__(self):
        return bool(self.name)


if __name__ == '__main__':
    api = TheTVDBAPI()
    flash = api.get_show_by_imdb_id('tt3107288')
    flash.get_newest_episode()