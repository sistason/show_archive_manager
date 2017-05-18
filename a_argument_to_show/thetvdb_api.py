import datetime
import json
import logging
import re
import time
from multiprocessing import Process, Queue
import requests


class TheTVDBAPI:
    API_KEY = "87EF0C7BB9CA4283"
    url = 'https://api.thetvdb.com'

    def __init__(self, test=False):
        logging.getLogger("requests").setLevel(logging.WARNING)

        self.jwt_token = None
        if not test:
            self.jwt_token = self.login()

        self.headers = {'Accept-Language': 'en', 'Accept': 'application/json',
                        'Authorization': 'Bearer {}'.format(self.jwt_token)}

    def login(self):
        logging.debug('Authenticating against TVDB-API...')
        data = json.dumps({'apikey': self.API_KEY})
        headers = {'Content-Type': 'application/json'}
        try:
            ret = requests.post(self.url + "/login", data=data, headers=headers, timeout=10)
            if ret.ok:
                logging.debug('  Authenticated!')
                ret_j = json.loads(ret.text)
                return ret_j.get('token')
            if 400 < ret.status_code < 499:
                logging.error('  Authentication failed! Invalid API-Key?')
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            logging.error('  Authentication failed! API down?')

    def get_shows_by_search(self, search, year=None):
        logging.debug('Getting shows matching "{}"...'.format(search))
        response = self._make_request('/search/series?name={}'.format(search))
        responses = self._validate_response_to_json(response)
        if year:
            responses = self._filter_search_by_year(responses, year)
        if len(responses) > 1:
            return [s for s in self._jsons_to_show_threaded(responses) if s]
        return [self._json_to_show(r) for r in responses]

    def get_show_by_imdb_id(self, imdb_id):
        logging.debug('Getting show by imdb_id "{}"...'.format(imdb_id))
        response = self._make_request('/search/series?imdbId={}'.format(imdb_id))
        responses = self._validate_response_to_json(response)
        return self._json_to_show(responses[0]) if responses else None

    def _json_to_show(self, response):
        show = TVDBShow(response, self) if response else None
        show.fill_data()
        return show if show else None

    def _jsons_to_show_threaded(self, responses):
        queue = Queue()
        process_list = []
        for response in responses:
            proc_ = Process(target=self._json_to_show_threaded, args=(response, queue))
            proc_.start()
            process_list.append(proc_)

        [p.join(5) for p in process_list]
        return [queue.get_nowait() for _ in range(queue.qsize())]

    def _json_to_show_threaded(self, response, queue):
        queue.put(self._json_to_show(response))

    def _filter_search_by_year(self, responses, year):
        return [r for r in responses if str(self.get_airdate(r).year) == str(year)]

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
                return requests.get(self.url + url, data=data, headers=self.headers, timeout=10)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                time.sleep(1)
            except Exception as e:
                logging.debug(
                    'Caught Exception "{}" while making a get-request to "{}"'.format(e.__class__, url))
                return

    def get_episode_data(self, tvdb_show, page=1):
        if page == 1:
            logging.debug('Getting episode_data for show "{}"...'.format(repr(tvdb_show)))
        data = []
        response = self._make_request('/series/{}/episodes?page={}'.format(tvdb_show.tvdb_id, page))
        if response is not None and response.ok:
            ret_j = json.loads(response.text)
            data.extend(ret_j.get('data', []))
            errors = ret_j.get('errors')
            if errors and not data:
                logging.warning('Getting episode_data for show "{}" showed errors: {}'.format(tvdb_show, errors))
                return []
            next_ = ret_j.get('links', {}).get('next')
            if next_ is not None:
                data.extend(self.get_episode_data(tvdb_show, page=next_))

        return data

    def get_imdb_id_from_tvdb_id(self, tvdb_id):
        response = self._make_request('/series/{}'.format(tvdb_id))
        response_j = self._validate_response_to_json(response)
        return response_j.get('imdbId', 'tt0')

    @staticmethod
    def get_airdate(data):
        try:
            return datetime.datetime.strptime(data.get('firstAired'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return datetime.datetime.fromtimestamp(0).date()

    def __bool__(self):
        return bool(self.jwt_token)


class TVDBShow:
    def __init__(self, json_result, api):
        self.raw = json_result
        self.api = api

        self.aired = self.api.get_airdate(json_result)
        self.name = json_result.get('seriesName', '')
        self.overview = json_result.get('overview', '') if json_result.get('overview') else ''
        self.tvdb_id = json_result.get('id', 0)
        self.imdb_id = ''

        self.seasons = {}
        self.episodes = []

    def fill_data(self):
        if self.imdb_id:
            return
        self.imdb_id = self.api.get_imdb_id_from_tvdb_id(self.tvdb_id)

        for ep_j in self.api.get_episode_data(self):
            self._add_episode(Episode(self, ep_j))

        if not self.seasons:
            logging.error('Could not get show data of "{}"!'.format(self.name))

    def _add_episode(self, episode):
        if episode:
            self.episodes.append(episode)
            if episode.season in self.seasons.keys():
                self.seasons[episode.season].add_episode(episode)
            else:
                self.seasons[episode.season] = Season(self, episode)

    def get_newest_episode(self):
        today = datetime.date.today()
        episodes_ = [ep for ep in self.episodes if ep.date <= today]
        return max(episodes_, key=lambda ep: ep.date) if episodes_ else {}

    def get_episodes_since(self, date):
        today = datetime.date.today()
        return [ep for ep in self.episodes if date <= ep.date <= today]

    def __repr__(self):
        return '{} [{}]'.format(self.name, self.imdb_id) if self.imdb_id else self.name

    def __str__(self):
        return self.name

    def str_verbose(self):
        return "{}\n{}".format(str(self), '\t\n'.join(map(lambda f: f.str_verbose(), self.seasons.values())))

    def __bool__(self):
        return bool(self.name) and bool(self.seasons)

    def get_storage_name(self):
        return '{} [{}]'.format(self.name, self.imdb_id)

    def get_brief(self):
        return '{:25} [{:9}] | {} | {:3} episodes | {}'.format(self.name[:25], self.imdb_id, self.aired.year,
                                                        len(self.episodes), self.overview[:40])

    def __len__(self):
        return len(self.episodes)


class Season:
    FORMAT = "Season {}"

    def __init__(self, show, init_episode):
        self.show = show
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

    def get_regex(self):
        return re.compile(r'(?i)s?0*(?P<season>{})'.format(self.number))

    def __repr__(self):
        return self.FORMAT.format(self.number)

    def str_verbose(self):
        return "{}: {}".format(str(self), ', '.join(map(lambda f: f.str_verbose(), self.episodes)))


class Episode:
    def __init__(self, show, json_data):
        self.show = show
        self.season = self._get_int_if_true(json_data, 'airedSeason', 0)
        self.episode = self._get_int_if_true(json_data, 'airedEpisodeNumber', 0)
        self.name = json_data.get('episodeName', '')
        self.date = self.show.api.get_airdate(json_data)
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

    def __repr__(self):
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
    api_ = TheTVDBAPI()
    show_ = api_.get_show_by_imdb_id(sys.argv[1])
    print(show_.get_newest_episode())
