import re
import json
import time
import logging
import requests
import datetime


def get_airdate(data):
    try:
        return datetime.datetime.strptime(data.get('firstAired'), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return datetime.datetime.fromtimestamp(0).date()


class TheTVDBAPI:
    API_KEY = "87EF0C7BB9CA4283"
    url = 'https://api.thetvdb.com/'

    def __init__(self, test=False):
        logging.getLogger("requests").setLevel(logging.WARNING)

        self.jwt_token = ''
        if not test:
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
            return ret_j.get('token')

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
        return [r for r in responses if str(get_airdate(r).year) == str(year)]

    @staticmethod
    def _validate_response_to_json(response):
        if response is not None and response.ok:
            ret_j = json.loads(response.text)
            return ret_j.get('data', []) if not ret_j.get('errors') else ret_j.get('errors')
        return {}

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

    def get_episode_data(self, tvdb_show, page=1):
        data = []
        response = self._make_request(self.url + 'series/{}/episodes?page={}'.format(tvdb_show.tvdb_id, page))
        if response is not None and response.ok:
            ret_j = json.loads(response.text)
            data.extend(ret_j.get('data', []))
            errors = ret_j.get('errors')
            if errors:
                logging.warning('Getting episode_data for show "{}" showed errors: {}'.format(tvdb_show, errors))
                return []
            next_ = ret_j.get('links', {}).get('next')
            if next_ is not None:
                data.extend(self.get_episode_data(tvdb_show, page=next_))

        return data

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

        if not self.seasons:
            logging.error('Could not get show data of "{}"!'.format(self.name))

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

    def get_episodes_since(self, date):
        today = datetime.date.today()
        return [ep for ep in self.episodes if date <= ep.date <= today]

    def __str__(self):
        return '{} [{}]'.format(self.name, self.imdb_id)

    def str_verbose(self):
        return "{}\n{}".format(str(self), '\t\n'.join(map(lambda f: f.str_verbose(), self.seasons.values())))

    def __bool__(self):
        return bool(self.name) and bool(self.seasons)


class Season:
    FORMAT = "Season {}"

    def __init__(self, init_episode):
        self.number = init_episode.season
        self.episodes = [init_episode]

    def add_episode(self, episode):
        if episode not in self.episodes:
            self.episodes.append(episode)

    def get_aired_episodes(self):
        today = datetime.date.today()
        return [ep for ep in self.episodes if ep.date <= today]

    def get_season_from_string(self, string_):
        match = re.match(self.FORMAT.format('(\d+)'), string_)
        return int(match.group(1)) if match else 0

    def __str__(self):
        return self.FORMAT.format(self.number)

    def str_verbose(self):
        return "{}: {}".format(str(self), ', '.join(map(lambda f: f.str_verbose(), self.episodes)))


class Episode:
    def __init__(self, json_data):
        self.season = self._get_int_if_true(json_data, 'airedSeason', 0)
        self.episode = self._get_int_if_true(json_data, 'airedEpisodeNumber', 0)
        self.name = json_data.get('episodeName', '')
        self.date = get_airdate(json_data)
        self.absolute_episode_number = self._get_int_if_true(json_data, 'absoluteNumber', 0)

    @staticmethod
    def _get_int_if_true(data, value, default):
        item = data.get(value, default)
        if type(item) is int:
            return item
        if type(item) is str and item.isdigit():
            return int(item)
        return default

    def get_regex(self):
        return re.compile(r'(?i)s?0*(?P<season>{s.season})[ex]0*(?P<episode>{s.episode})(?!\d)'.format(s=self))

    def __str__(self):
        return "s{s.season:02}e{s.episode:02}".format(s=self)

    def str_verbose(self):
        return "{}: {} [#{}]".format(str(self), self.name, self.absolute_episode_number)

    def __bool__(self):
        return bool(self.name)

    def __eq__(self, other):
        return (other and self.season == other.season and self.episode == other.episode and
                self.absolute_episode_number == other.absolute_episode_number and self.name == other.name)


if __name__ == '__main__':
    import sys
    api = TheTVDBAPI()
    show = api.get_show_by_imdb_id(sys.argv[1])
    print(show.get_newest_episode())
