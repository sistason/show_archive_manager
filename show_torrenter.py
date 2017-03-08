import re
import requests
import time
import logging
import bs4


QUALITY_REGEX = {
    'quality': {
        '1080p': re.compile(r'(?i)1080p'),
        '480p': re.compile(r'(?i)480p|HDTV'),
        '720p': re.compile(r'(?i)720p'),
    },
    'encoder': {
        'x264': re.compile(r'(?i)[hx]264'),
        'x265': re.compile(r'(?i)[hx]265'),
        'xvid': re.compile(r'(?i)XviD'),
    }
}


class ShowDownload:
    def __init__(self, status):
        self.status = status
        self.download_links_behind = None
        self.download_links_missing = None

    def __str__(self):
        return str(self.status)


class Status2Torrent:
    def __init__(self, quality, update_missing=False):
        self.update_missing = update_missing
        self.quality = quality
        self.headers = {}

    def get_torrent(self, status):
        show_download = ShowDownload(status)
        show_download.download_links_behind = self.get_episodes(status.show.name, status.episodes_behind)
        logging.debug('Found {} links to get "{}" up-to-date'.format(len(show_download.download_links_behind),
                                                                     status.show.name))
        if self.update_missing:
            show_download.download_links_missing = self.get_episodes(status.show.name, status.episode_holes)
            logging.debug('Found {} links to get "{}" complete'.format(len(show_download.download_links_missing),
                                                                       status.show.name))

        return show_download

    def get_episodes(self, name, episodes):
        links_ = []
        for episode in episodes:
            found_links = self._search(name, episode)
            url = self._to_url(self._filter_searches(found_links, episode))
            if url:
                links_.append(url)

        return links_

    def _search(self, name, episode):
        return NotImplementedError

    def _to_url(self, match):
        return NotImplementedError

    def _filter_searches(self, links_, episode):
        """ Return the first matching link (the earlier, the better matching) """
        for link in links_:
            if self._torrent_matches(link.text, episode):
                return link

    def _torrent_matches(self, title, episode):
        for filter_ in [episode.get_regex(),
                        QUALITY_REGEX['encoder'].get(self.quality.get('encoder')),
                        QUALITY_REGEX['quality'].get(self.quality.get('quality'))]:
            if not filter_.search(title):
                return False
        return True

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


class Status2Piratebay(Status2Torrent):
    url = 'https://thepiratebay.org'

    def _search(self, name, episode):
        query = "{} {}".format(name, str(episode))
        response = self._make_request(self.url + '/search/{}/0/99/205'.format(query))
        if response.ok:
            return self._parse_piratebay_response(response.text)

    @staticmethod
    def _parse_piratebay_response(text):
        bs4_ = bs4.BeautifulSoup(text, "html5lib")
        return bs4_.find_all('a', attrs={'class': 'detLink'})

    def _to_url(self, match):
        try:
            return self.url + match.attrs.get('href')
        except (AttributeError, TypeError):
            return None

SITES = {'piratebay': Status2Piratebay, 'default': Status2Piratebay}

if __name__ == '__main__':
    s2t = Status2Piratebay({'quality': '720p', 'encoder': 'x264'})
    from thetvdb_api import Episode
    links = s2t.get_episodes('supergirl', [Episode({'airedSeason': 2, 'airedEpisodeNumber': 13})])
    print(links)
