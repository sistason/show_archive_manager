import datetime
import asyncio
import logging
import os
import re

from a_argument_to_show.thetvdb_api import Episode
from premiumize_me_dl.premiumize_me_api import PremiumizeMeAPI
DOWNLOADERS = {'premiumize.me': PremiumizeMeAPI, 'default': PremiumizeMeAPI}


class Download:
    def __init__(self, information, reference, transfer, downloader):
        self.information = information
        self.reference = reference
        self.downloader = downloader

        self.transfer = transfer
        self.start_time = None

        self.retries = 10


class Torrent2Download:
    CONCURRENT_DOWNLOADS = 15

    def __init__(self, login, event_loop):
        self.event_loop = event_loop
        downloader = DOWNLOADERS.get('default')
        self.torrent_downloader = downloader(login, self.event_loop)

        self.download_semaphore = asyncio.Semaphore(self.CONCURRENT_DOWNLOADS)

        self.shutdown = False
        self.tasks = []

    async def _download_torrent(self, torrent, information):
        for torrent_link in torrent.links:
            async with self.download_semaphore:
                if self.shutdown:
                    return

                _dn = re.search(r'&dn=(.*?)&', torrent_link)
                logging.info('Uploading torrent {} ({})...'.format(torrent.reference,
                                                                   _dn.group(1) if _dn else torrent_link[40:80]))
                transfer = await self.torrent_downloader.upload(torrent_link)
                if not transfer:
                    return

                # cleanup on shutdown interruption
                if self.shutdown:
                    await self.torrent_downloader.delete(transfer)
                    return

                download_directory = os.path.join(information.download_directory,
                                                  str(information.show.get_storage_name()))
                if type(torrent.reference) == Episode:
                    season_ = information.show.seasons.get(torrent.reference.season)
                    download_directory = os.path.join(download_directory, str(season_))

                logging.info('Downloading {}...'.format(transfer.name))
                success = await self.torrent_downloader.download_transfer(transfer, download_directory)
                if success:
                    logging.info('Success! Deleting torrent...')
                    await self.torrent_downloader.delete(transfer)
                    return success
                logging.error('Error! Could not download torrent, was {}'.format(success))

    async def close(self):
        self.shutdown = True
        [w.cancel() for w in self.tasks]

        logging.info('Waiting 5 secs for all downloaders to abort...')
        await asyncio.wait(self.tasks, timeout=5)

        await self.torrent_downloader.close()

    async def download(self, information):
        logging.info('Downloading {}...'.format(information.show.name))

        downloads = asyncio.gather(*[self._download_torrent(torrent, information)
                                     for torrent in information.torrents if torrent])
        self.tasks.append(downloads)
        await downloads

    def __bool__(self):
        return bool(self.torrent_downloader)


class Torrent2Download_:
    CHECK_EVERY = 2
    WORKER_PER_SHOW = 5

    def __init__(self, login, event_loop):
        self.event_loop = event_loop
        downloader = DOWNLOADERS.get('default')
        self.torrent_downloader = downloader(login, self.event_loop)

        self.downloads_queue = asyncio.Queue()
        self.all_workers = []

        self.shutdown = False

    async def close(self):
        self.shutdown = True
        [w.cancel() for w in self.all_workers]

        await asyncio.wait(self.all_workers, timeout=self.CHECK_EVERY)

        await self.torrent_downloader.close()

    async def download_from_cache(self, information):
        show_transfers = [transfer for transfer in await self.torrent_downloader.get_transfers()
                          if information.show.name in transfer.name]
        for show_transfer in show_transfers:
            for episode in information.status.episodes_missing:
                if episode.get_regex().search(show_transfer.name):
                    logging.info('{} - {} is already available'.format(information.show, episode))
                    download = Download(information, episode, show_transfer, self.torrent_downloader)
                    await self.downloads_queue.put(download)
                    information.status.episodes_missing.remove(episode)
                    for torrent in information.torrents:
                        if torrent.reference == episode:
                            information.torrents.remove(torrent)

            for season in information.status.seasons_missing:
                if season.get_regex().search(show_transfer.name):
                    logging.info('{} - Season {} is already available'.format(information.show, season.number))
                    download = Download(information, season, show_transfer, self.torrent_downloader)
                    await self.downloads_queue.put(download)
                    information.status.seasons_missing.remove(season)
                    for torrent in information.torrents:
                        if torrent.reference == season:
                            information.torrents.remove(torrent)

        return information

    async def download(self, information):
        logging.info('Downloading {}...'.format(information.show.name))

        await self._start_torrenting(information)

        workers = [asyncio.ensure_future(self.worker()) for _ in range(self.WORKER_PER_SHOW)]
        self.all_workers.extend(workers)
        await asyncio.gather(*workers)

    async def _start_torrenting(self, information):
        logging.debug('Start torrenting {}...'.format(information.show.name))

        information = await self.download_from_cache(information)

        # FIXME: is the list the same reference for all tasks? call by value or reference?
        transfer_list_ = []
        tasks = [asyncio.ensure_future(self._upload_torrent(torrent, transfer_list_, information))
                        for torrent in information.torrents]
        await asyncio.gather(*tasks)

    async def _upload_torrent(self, torrent, transfer_list_, information):
        if torrent is None:
            return
        for link in torrent.links:
            transfer = await self.torrent_downloader.upload(link)
            if transfer is not None:
                if transfer.id not in transfer_list_:
                    transfer_list_.append(transfer.id)
                    download = Download(information, torrent.reference, transfer, self.torrent_downloader)
                    await self.downloads_queue.put(download)
                    return
                logging.warning('Link "{}" for "{}" was a duplicate'.format(link[:50], torrent.reference))

    async def worker(self):
        try:
            while True:
                download = self.downloads_queue.get_nowait()
                # Allow a context switch here so that other workers can get_nowait and realize the queue is only 1 elem
                await asyncio.sleep(.1)

                if download.start_time is None:
                    download.start_time = datetime.datetime.now()

                download.transfer = await download.downloader.get_transfer(download.transfer)
                finished = download.downloader.is_transfer_finished(download.transfer, download.start_time)

                if finished is None:
                    self.downloads_queue.put_nowait(download)
                elif finished is True:
                    if await self._worker_handle_download(download):
                        self.downloads_queue.put_nowait(download)

                self.downloads_queue.task_done()

                await asyncio.sleep(5)

        except asyncio.QueueEmpty:
            logging.debug('Downloads_Queue is empty, work is finished.')
        except RuntimeError:
            logging.debug('Worker was being cancelled.')
        except Exception as e:
            logging.error('Worker got exception: "{}"'.format(repr(e)))

    async def _worker_handle_download(self, download):
        download_directory = os.path.join(download.information.download_directory,
                                          str(download.information.show.get_storage_name()))
        if type(download.reference) == Episode:
            season_ = download.information.show.seasons.get(download.reference.season)
            download_directory = os.path.join(download_directory, str(season_))

        os.makedirs(download_directory, exist_ok=True)

        file_ = await download.downloader.get_file_from_transfer(download.transfer)
        if file_:
            if await download.downloader.download_file(file_, download_directory):
                await self._cleanup(download, file_)
                logging.debug('Finished downloading {} {}'.format(download.information.show.name,
                                                                  download.reference))
            elif download.retries > 0:
                download.retries -= 1
                return True
        else:
            logging.error('Download {} {} was not downloadeable.'.format(download.information.show.name,
                                                                         download.reference))

    @staticmethod
    async def _cleanup(download, file_):
        logging.info('Cleaning up {}'.format(file_.name))
        await download.downloader.delete(file_)

    def __bool__(self):
        return bool(self.torrent_downloader)
