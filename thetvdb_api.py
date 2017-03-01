import json
import time
import logging
import requests
import datetime


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

    def get_current_episode(self, tvdb_show):
        responses = self._make_request(self.url + 'series/{}/episodes'.format(tvdb_show.tvdb_id))
        newest_episode = max([(r.get('firstAired','0-0-0'), r) for r in responses])
        print(newest_episode)
        se, ep = newest_episode.get('airedSeason', 0), newest_episode.get('airedEpisode', 0)
        return int(se) if se.isdigit() else 0, int(ep) if ep.isdigit() else 0

    def get_imdb_id_from_tvdb_id(self, tvdb_id):
        response = self._make_request(self.url + 'series/{}'.format(tvdb_id))
        response_j = self._validate_response_to_json(response)
        return response_j.get('imdbId', 'tt0')


class TVDBShow:
    def __init__(self, json_result, api):
        self.raw = json_result
        self.api = api
        try:
            self.aired = datetime.datetime.strptime(json_result.get('firstAired', '1970-1-1'), '%Y-%m-%d').date()
        except ValueError:
            self.aired = datetime.datetime.fromtimestamp(0).date()

        self.name = json_result.get('seriesName', '')
        self.tvdb_id = json_result.get('id', '0')
        self.imdb_id = api.get_imdb_id_from_tvdb_id(self.tvdb_id)

    def get_current_episode(self):
        return self.api.get_current_episode(self)

    def __str__(self):
        return '{} [{}]'.format(self.name, self.imdb_id)
