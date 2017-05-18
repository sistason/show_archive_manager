import asyncio
import logging
import re

from c_status_to_torrent.piratebay import PiratebayGrabber


class Status2Torrent:
    def __init__(self, quality, event_loop):
        torrenter = GRABBER.get('default')
        self.torrent_grabber = torrenter(event_loop)
        self.quality = quality if quality else {}

    def close(self):
        self.torrent_grabber.close()

    async def get_torrents(self, information):
        logging.debug('Getting torrents for {} ({} eps)...'.format(information.show.name, len(information.status)))

        torrents = await self._get_torrents_async(information)
        logging.info('Found {} torrents to get "{}" up-to-date'.format(sum([len(l) for l in torrents if l]),
                                                                        information.show.name))

        return torrents

    async def _get_torrents_async(self, information):
        episode_tasks = [asyncio.ensure_future(self.get_torrent_for_episode(information.show.name, ep))
                         for ep in information.status.episodes_missing]
        season_tasks = [asyncio.ensure_future(self.get_torrent_for_season(information.show.name, se))
                         for se in information.status.seasons_missing]

        return await asyncio.gather(*episode_tasks, *season_tasks)

    async def get_torrent_for_season(self, name, season):
        logging.debug('{} - {}: Searching for torrents...'.format(name, season))

        results = await self.torrent_grabber.search(name, season)
        filtered_results = self.filter_searches(results, season)

        logging.debug('{} - {}: Found {:2} torrents, {} of those match'.format(name, season, len(results),
                                                                           len(filtered_results)))

        sorted_results = self.sort_results(filtered_results)
        if sorted_results:
            return Torrent(season, sorted_results)

    async def get_torrent_for_episode(self, name, episode):
        logging.debug('{} - : Searching for torrents...'.format(name, episode))

        results = await self.torrent_grabber.search(name, episode)
        filtered_results = self.filter_searches(results, episode)

        logging.debug('{}: Found {:2} torrents, {} of those match'.format(episode, len(results),
                                                                           len(filtered_results)))

        sorted_results = self.sort_results(filtered_results)
        if sorted_results:
            return Torrent(episode, sorted_results)

    def _torrent_matches(self, result, object):
        for filter_re in [object.get_regex(),
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
    def __init__(self, reference, results):
        self.reference = reference
        self.links = [t.magnet for t in results]

    def __len__(self):
        return len(self.links)


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