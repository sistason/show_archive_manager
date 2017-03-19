import asyncio
import logging
import re

import aiohttp
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
    def __init__(self, episode, results):
        self.episode = episode
        self.links = [t.magnet for t in results]


class PirateBayResult:
    def __init__(self, beautiful_soup_tag):
        self.title = self.magnet = ''
        self.seeders = self.leechers = 0
        try:
            tds = beautiful_soup_tag.find_all('td')
            self.title = tds[1].a.text
            self.magnet = tds[1].find_all('a')[1].attrs.get('href')
            self.seeders = int(tds[-2].text)
            self.leechers = int(tds[-1].text)
        except (IndexError, ValueError, AttributeError):
            return

    def __bool__(self):
        return bool(self.title)


class Status2Torrent:
    def __init__(self, torrent_site, quality, update_missing=False):
        self.event_loop = asyncio.get_event_loop()
        self.torrent_grabber = GRABBER.get(torrent_site)(self.event_loop) if torrent_site in GRABBER else None
        if self.torrent_grabber is None:
            logging.error('Requested torrent site "{}" not available! Cannot continue!'.format(torrent_site))
        self.quality = quality if quality else {}
        self.update_missing = update_missing

    def close(self):
        self.torrent_grabber.close()

    def get_torrents(self, status):
        logging.debug('Getting torrents for {} ({} eps)...'.format(status.show.name, len(status)))
        show_download = ShowDownload(status)

        show_download.torrents_behind = self._get_specific_torrents(status.episodes_behind, status)
        logging.debug('Found {} links to get "{}" up-to-date'.format(len(show_download.torrents_behind),
                                                                     status.show.name))
        if self.update_missing:
            show_download.torrents_missing = self._get_specific_torrents(status.episodes_missing, status)
            logging.debug('Found {} links to get "{}" complete'.format(len(show_download.torrents_missing),
                                                                       status.show.name))

        return show_download

    def _get_specific_torrents(self, episodes, status):
        episode_tasks = [asyncio.ensure_future(self.get_torrent_for_episode(status.show.name, behind))
                                 for behind in episodes]
        self.event_loop.run_until_complete(asyncio.gather(*episode_tasks))
        return [task.result() for task in episode_tasks]

    async def get_torrent_for_episode(self, name, episode):
        logging.debug('{}: Searching for torrents...'.format(episode))

        results = await self.torrent_grabber.search(name, episode)
        filtered_results = self.filter_searches(results, episode)

        logging.debug('{}: Found {} torrents, {} of those matching'.format(episode, len(results),
                                                                           len(filtered_results)))

        sorted_results = self.sort_results(filtered_results)
        if sorted_results:
            return Torrent(episode, sorted_results)

    def _torrent_matches(self, result, episode):
        for filter_re in [episode.get_regex(),
                          QUALITY_REGEX['encoder'].get(self.quality.get('encoder')),
                          QUALITY_REGEX['quality'].get(self.quality.get('quality'))]:
            if filter_re and not filter_re.search(result.title):
                return False
        return True

    def filter_searches(self, results, episode):
        return [result for result in results if self._torrent_matches(result, episode)]

    @staticmethod
    def sort_results(results):
        return sorted(results, key=lambda f: f.seeders, reverse=True)

    def __bool__(self):
        return True


class PiratebayGrabber:
    url = 'https://thepiratebay.org'

    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.aiohttp_session = None
        self.max_simultaneous_requests = asyncio.Semaphore(10)

        self.parser = PirateBayParser()

    def close(self):
        if self.aiohttp_session is not None:
            self.aiohttp_session.close()

    async def _make_request(self, url):
        async with self.max_simultaneous_requests:
            if self.aiohttp_session is None:
                self.aiohttp_session = aiohttp.ClientSession(loop=self.event_loop)
            for retry in range(3):
                try:
                    async with self.aiohttp_session.post(url, timeout=5) as r_:
                        text = await r_.text()
                        if r_.status == 200:
                            return text
                except (aiohttp.errors.TimeoutError, aiohttp.errors.ClientConnectionError):
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.debug(
                        'Caught Exception "{}" while making a get-request to "{}"'.format(e.__class__, url))
                    return

    async def search(self, name, episode):
        query = "{} {}".format(name, str(episode))
        response = await self._make_request(self.url + '/search/{}/0/99/205'.format(query))
        if response:
            return self.parser.parse_piratebay_response(response)
        return []


class PirateBayParser:
    @staticmethod
    def parse_piratebay_response(text):
        bs4_response = bs4.BeautifulSoup(text, "html5lib")
        main_table = bs4_response.find('table', attrs={'id': 'searchResult'})
        return [PirateBayResult(tag) for tag in main_table.find_all('tr')[1:]]


GRABBER = {'piratebay': PiratebayGrabber, 'default': PiratebayGrabber}

if __name__ == '__main__':
    event_loop_ = asyncio.get_event_loop()
    grabber_ = PiratebayGrabber(event_loop_)
    s2t = Status2Torrent(grabber_, {'quality': '720p', 'encoder': 'x264'})

    from thetvdb_api import Episode
    logging.basicConfig(format='%(message)s',
                        level=logging.DEBUG)
    link_ = event_loop_.create_task(s2t.get_torrent_for_episode('supergirl',
                                                                Episode(None,
                                                                        {'airedSeason': 2, 'airedEpisodeNumber': 13})))
    event_loop_.run_until_complete(link_)
    event_loop_.close()
    s2t.torrent_grabber.close()
    print(link_.result().links)
