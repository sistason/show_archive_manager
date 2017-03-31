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

        self.retries = 5


class Torrent2Download:
    CHECK_EVERY = 5
    WORKER_PER_SHOW = 5

    def __init__(self, downloader, login, event_loop):
        self.event_loop = event_loop
        self.torrent_downloader = downloader(login, self.event_loop)

        self.downloads_queue = asyncio.Queue()
        self.all_workers = []

        self.transfers = []
        self.shutdown = False
        self._transfers_updater = None

    async def close(self):
        self.shutdown = True
        [w.cancel() for w in self.all_workers]

        if self._transfers_updater is not None:
            for _ in range(self.CHECK_EVERY*2):
                if self._transfers_updater.done():
                    break
                await asyncio.sleep(1)

        asyncio.wait(self.all_workers, timeout=self.CHECK_EVERY)

        self.torrent_downloader.close()

    async def _update_transfers(self):
        self.transfers = await self.torrent_downloader.get_transfers()
        for _ in range(self.CHECK_EVERY):
            if self.shutdown:
                return
            await asyncio.sleep(1)
        asyncio.ensure_future(self._update_transfers())

    async def download(self, information):
        logging.info('Downloading {}...'.format(information.show.name))

        await self._start_torrenting(information)

        workers = [asyncio.ensure_future(self.worker()) for _ in range(self.WORKER_PER_SHOW)]
        self.all_workers.extend(workers)
        await asyncio.gather(*workers)

    async def _start_torrenting(self, information):
        logging.debug('Start torrenting {}...'.format(information.show.name))

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
                # Allow a context switch here so that other workers can get_nowait and realize the queue is only 1 elem
                await asyncio.sleep(.1)

                if self._is_transfer_ready_to_download(download):
                    insert_again = await self._worker_handle_download(download)
                else:
                    insert_again = await self._worker_handle_transfer_progress(download)

                if insert_again:
                    self.downloads_queue.put_nowait(download)

                self.downloads_queue.task_done()

                await asyncio.sleep(5)

        except asyncio.QueueEmpty:
            logging.debug('Downloads_Queue is empty, work is finished.')
        except RuntimeError:
            logging.debug('Worker was being cancelled.')
        except Exception as e:
            logging.error('Worker got exception: "{}"'.format(repr(e)))

    @staticmethod
    async def _worker_handle_transfer_progress(download):
        if download.transfer is None:
            logging.error('Error torrenting {}: Torrent not found anymore!'.format(
                download.information.show.name))
        elif download.transfer.is_running():
            logging.debug('{} {}: {}'.format(download.information.show.name, download.episode,
                                             download.transfer.status_msg()))
            return True
        else:
            logging.error('Error torrenting {}: {}'.format(download.transfer.name,
                                                           download.transfer.message))

    async def _worker_handle_download(self, download):
        success = await self._download(download)
        if success:
            await self._cleanup(download)
            logging.debug('Finished downloading {} {}'.format(download.information.show.name,
                                                              download.episode))
        elif download.retries > 0:
            download.retries -= 1
            return True
        else:
            logging.error('Download {} {} was not downloadeable.'.format(download.information.show.name,
                                                                         download.episode))

    def _get_torrent_transfer(self, upload):
        for transfer in self.transfers:
            if transfer.id == upload.id:
                return transfer

    def _is_transfer_ready_to_download(self, download):
        transfer = self._get_torrent_transfer(download.upload)
        download.transfer = transfer
        return transfer is not None and not transfer.is_running() and transfer.status != 'error'

    @staticmethod
    async def _download(download):
        episode_directory = os.path.join(download.information.download_directory,
                                         str(download.information.show.get_storage_name()),
                                         str(download.information.show.seasons.get(download.episode.season)))
        os.makedirs(episode_directory, exist_ok=True)

        file_ = await download.downloader.get_file_from_transfer(download.transfer)
        if file_:
            await download.downloader.download_file(file_, episode_directory)

    @staticmethod
    async def _cleanup(download):
        logging.info('Cleaning up {}'.format(download.upload.name))
        await download.downloader.delete(download.upload)

    def __bool__(self):
        return bool(self.torrent_downloader)
