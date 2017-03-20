import asyncio
import logging
import re

from c_status_to_torrent.piratebay import PiratebayGrabber


class Status2Torrent:
    def __init__(self, torrenter, quality, update_missing=False):
        self.event_loop = asyncio.get_event_loop()
        self.torrent_grabber = torrenter(self.event_loop)
        self.quality = quality if quality else {}
        self.update_missing = update_missing

    def close(self):
        self.torrent_grabber.close()

    async def get_torrents(self, information):
        logging.debug('Getting torrents for {} ({} eps)...'.format(information.show.name, len(information.status)))

        torrents = await self._get_specific_torrents(information.status.episodes_behind, information)
        logging.debug('Found {} links to get "{}" up-to-date'.format(len(torrents),
                                                                     information.show.name))
        if self.update_missing:
            torrents_missing = await self._get_specific_torrents(information.status.episodes_missing, information)
            logging.debug('Found {} links to get "{}" complete'.format(len(torrents_missing),
                                                                       information.show.name))
            torrents.extend(torrents_missing)

        return torrents

    async def _get_specific_torrents(self, episodes, information):
        episode_tasks = [asyncio.ensure_future(self.get_torrent_for_episode(information.show.name, ep))
                                 for ep in episodes]
        return await asyncio.gather(*episode_tasks)

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


class Torrent:
    def __init__(self, episode, results):
        self.episode = episode
        self.links = [t.magnet for t in results]


GRABBER = {'piratebay': PiratebayGrabber, 'default': PiratebayGrabber}


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