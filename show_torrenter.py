import re
import requests
import time
import logging
import bs4


QUALITY_REGEX = {
    '1080p': re.compile(r'(?i)1080p'),
    '480p': re.compile(r'(?i)480p|HDTV'),
    '720p': re.compile(r'(?i)720p'),
    'x264': re.compile(r'(?i)[hx]264'),
    'x265': re.compile(r'(?i)[hx]265'),
    'xvid': re.compile(r'(?i)XviD'),
}


class Status2Torrent:
    def __init__(self, quality, update_missing=False):
        self.update_missing = update_missing
        self.quality = quality
        self.headers = {}

    def get_torrent(self, status):
        links = self._get_episodes(status.show.name, status.episodes_behind)
        if self.update_missing:
            links.extend(self._get_episodes(status.show.name, status.episodes_holes))

        return links

    def _get_episodes(self, name, episodes):
        links = []
        for episode in episodes:
            found_links = self._search_piratebay("{} {}".format(name, str(episode)))
            match = self._filter_searches(found_links, episode)
            if match:
                links.append(match)

        return links

    def _filter_searches(self, links, episode):
        """ Return the first matching link (the earlier, the better matching) """
        for link in links:
            if self._torrent_matches(link.text, episode):
                return link

    def _torrent_matches(self, title, episode):
        for filter in [episode.get_regex(),
                       QUALITY_REGEX.get(self.quality.get('encoder')),
                       QUALITY_REGEX.get(self.quality.get('quality'))]:
            if not filter.search(title):
                return False
        return True

    def _search_piratebay(self, query):
        response = self._make_request('https://thepiratebay.org/search/{}/0/99/205'.format(query))
        if response.ok:
            return self._parse_piratebay_response(response.text)

    def _parse_piratebay_response(self, text):
        bs4_ = bs4.BeautifulSoup(text, "html5lib")
        return bs4_.find_all('a', attrs={'class': 'detLink'})

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


if __name__ == '__main__':
    s2t = Status2Torrent({'quality': '720p', 'encoder': 'x264'})
    from thetvdb_api import Episode
    links = s2t._get_episodes('supergirl', [Episode({'airedSeason': 2, 'airedEpisodeNumber': 13})])
    print([l.attrs.get('href', None) for l in links])

