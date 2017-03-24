import asyncio
import logging
from time import sleep
import os

from premiumize_me_dl.premiumize_me_api import PremiumizeMeAPI
DOWNLOADERS = {'premiumize.me': PremiumizeMeAPI, 'default': PremiumizeMeAPI}


class Download:
    def __init__(self, information, episode, upload, downloader):
        self.information = information
        self.episode = episode
        self.downloader = downloader

        self.upload = upload
        self.transfer = None


class Torrent2Download:
    CHECK_EVERY = 5
    MAX_WORKERS = 5

    def __init__(self, downloader, login, event_loop):
        self.event_loop = event_loop
        self.torrent_downloader = downloader(login, self.event_loop)

        self.downloads_queue = asyncio.Queue()

        self.transfers = []
        self.shutdown = False
        self._transfers_updater = None

    def close(self):
        self.shutdown = True
        if self._transfers_updater is not None:
            for _ in range(self.CHECK_EVERY*2):
                if self._transfers_updater.done():
                    break
                sleep(1)

        self.torrent_downloader.close()

    async def _update_transfers(self):
        self.transfers = await self.torrent_downloader.get_transfers()
        if not self.shutdown:
            await asyncio.sleep(self.CHECK_EVERY)
            asyncio.ensure_future(self._update_transfers())

    async def download(self, information):
        logging.info('Downloading {}...'.format(information.show.name))

        await self._start_torrenting(information)

        workers = [asyncio.ensure_future(self.worker()) for _ in range(self.MAX_WORKERS)]
        await asyncio.gather(*workers)
        print('ALl workers gathered')
        await self.downloads_queue.join()
        print('ALl workers joined')

    async def _start_torrenting(self, information):
        logging.info('Start torrenting {}...'.format(information.show.name))

        upload_ids = []
        upload_tasks = [asyncio.ensure_future(self._upload_torrent(torrent, upload_ids, information))
                        for torrent in information.torrents]
        await asyncio.gather(*upload_tasks)

        if self._transfers_updater is None:
            await self._wait_for_transfers()

    async def _wait_for_transfers(self):
        self._transfers_updater = asyncio.ensure_future(self._update_transfers())
        for _ in range(10):
            if self.transfers:
                break
            await asyncio.sleep(1)
        else:
            logging.warning('Could not get torrent-transfers in time!')

    async def _upload_torrent(self, torrent, upload_ids, information):
        if torrent is None:
            return
        for link in torrent.links:
            upload_ = await self.torrent_downloader.upload(link)
            if upload_ is not None:
                if upload_.id not in upload_ids:
                    upload_ids.append(upload_.id)
                    download = Download(information, torrent.episode, upload_, self.torrent_downloader)
                    await self.downloads_queue.put(download)
                    return
                logging.warning('Link "{}" for episode "{}" was a duplicate'.format(link[:50], torrent.episode))

    async def worker(self):
        try:
            while True:
                download = self.downloads_queue.get_nowait()
                download.transfer = self._get_torrent_transfer(download.upload)

                if self._is_transfer_ready_to_download(download.transfer):
                    await self._download(download)
                    await self._cleanup(download)
                    logging.debug('Finished downloading {} {}'.format(download.information.show.name,
                                                                      download.episode))
                else:
                    if download.transfer is None:
                        logging.error('Error torrenting {}: Torrent not found anymore!'.format(
                                download.information.show.name))
                    elif download.transfer.is_running():
                        self.downloads_queue.put_nowait(download)
                    else:
                        logging.error('Error torrenting {}: {}'.format(download.transfer.name,
                                                                       download.transfer.message))

                self.downloads_queue.task_done()
                print(self.downloads_queue.qsize())

                await asyncio.sleep(5)

        except asyncio.QueueEmpty:
            logging.debug('Downloads_Queue is empty, work is finished.')
        except Exception as e:
            print('worker-e:', e)
        print('worker finished!')

    def _get_torrent_transfer(self, upload):
        for transfer in self.transfers:
            if transfer.id == upload.id:
                return transfer

    @staticmethod
    def _is_transfer_ready_to_download(transfer):
        return transfer is not None and not transfer.is_running() and transfer.status != 'error'

    @staticmethod
    async def _download(download):
        episode_directory = os.path.join(download.information.download_directory,
                                         str(download.information.show.get_storage_name()),
                                         str(download.information.show.seasons.get(download.episode.season)))
        os.makedirs(episode_directory, exist_ok=True)

        await download.downloader.download_file(download.transfer, episode_directory)

    @staticmethod
    async def _cleanup(download):
        logging.info('Cleaning up {}'.format(download.upload.name))
        await download.downloader.delete(download.upload)

    def __bool__(self):
        return bool(self.torrent_downloader)
