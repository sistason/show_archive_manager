import re
import asyncio
import aiohttp
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
        self.torrents_behind = []
        self.torrents_missing = []

    def __str__(self):
        return str(self.status)


class Torrent:
    def __init__(self, episode, links):
        self.episode = episode
        self.links = links


class Status2Torrent:
    def __init__(self, quality, event_loop, update_missing=False):
        self.update_missing = update_missing
        self.quality = quality if quality else {}

        self.event_loop = event_loop
        self.aiohttp_session = None
        self.max_simultaneous_requests = asyncio.Semaphore(10)
        self.headers = {}

    async def get_torrents(self, status):
        logging.debug('Getting torrents for {} ({} eps)...'.format(status.show.name, len(status)))
        show_download = ShowDownload(status)

        episodes_behind_tasks = [asyncio.ensure_future(self.get_episode(status.show.name, behind))
                                 for behind in status.episodes_behind]
        episodes_missing_tasks = [asyncio.ensure_future(self.get_episode(status.show.name, missing))
                                  for missing in status.episodes_missing if self.update_missing]

        await asyncio.gather(*episodes_behind_tasks, *episodes_missing_tasks)
        show_download.torrents_behind = [task.result() for task in episodes_behind_tasks]
        show_download.torrents_missing = [task.result() for task in episodes_missing_tasks]

        logging.debug('Found {} links to get "{}" up-to-date'.format(len(show_download.torrents_behind),
                                                                     status.show.name))
        if self.update_missing:
            logging.debug('Found {} links to get "{}" complete'.format(len(show_download.torrents_missing),
                                                                       status.show.name))
        return show_download

    async def get_episode(self, name, episode):
        logging.debug('{}: Searching for torrents...'.format(episode))

        found_links = await self._search(name, episode)
        print(found_links)
        logging.debug('{}: Found {} torrents'.format(episode, len(found_links)))

        urls = [self._to_url(t) for t in self._filter_searches(found_links, episode)]
        if urls:
            logging.debug('{}: Found links "{}"'.format(episode, urls))
            return Torrent(episode, urls)

    async def _search(self, name, episode):
        return []

    def _to_url(self, match):
        return NotImplementedError

    def _filter_searches(self, links_, episode):
        """ Return the first matching link (the earlier, the better matching) """
        return [link for link in links_ if self._torrent_matches(link.text, episode)]

    def _torrent_matches(self, title, episode):
        for filter_ in [episode.get_regex(),
                        QUALITY_REGEX['encoder'].get(self.quality.get('encoder')),
                        QUALITY_REGEX['quality'].get(self.quality.get('quality'))]:
            if not filter_ or not filter_.search(title):
                return False
        return True

    async def _make_request(self, url, data=None, params=None):
        """ Do a request, take care of timeouts and exceptions """
        if data is None:
            data = {}
        if params is None:
            params = {}
        async with self.max_simultaneous_requests:
            if self.aiohttp_session is None:
                self.aiohttp_session = aiohttp.ClientSession(loop=self.event_loop)
            for _ in range(3):
                try:
                    async with self.aiohttp_session.post(url, data=data,
                                                         params=params, timeout=5) as r_:
                        text = await r_.text()
                        if r_.status == 200:
                            return text
                except (aiohttp.errors.TimeoutError, aiohttp.errors.ClientConnectionError):
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.debug(
                        'Caught Exception "{}" while making a get-request to "{}"'.format(e.__class__, url))
                    return

    def close(self):
        self.aiohttp_session.close()

    def __bool__(self):
        return True


class Status2Piratebay(Status2Torrent):
    url = 'https://thepiratebay.org'

    async def _search(self, name, episode):
        query = "{} {}".format(name, str(episode))
        response = await self._make_request(self.url + '/search/{}/0/99/205'.format(query))
        if response:
            return self._parse_piratebay_response(response)
        return []

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
    event_loop_ = asyncio.get_event_loop()
    s2t = Status2Piratebay({'quality': '720p', 'encoder': 'x264'}, event_loop_)
    from thetvdb_api import Episode
    link_ = event_loop_.create_task(s2t.get_episode('supergirl',
                                                    Episode(None, {'airedSeason': 2, 'airedEpisodeNumber': 13})))
    event_loop_.run_until_complete(link_)
    event_loop_.close()
    s2t.close()
    print(link_.result().links)
