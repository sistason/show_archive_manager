import asyncio
import logging
import time
from multiprocessing import Value, Queue, Process

from d_torrent_to_download.torrent_download_worker import TorrentDownloadWorker
from premiumize_me_dl.premiumize_me_api import PremiumizeMeAPI


class Torrent2Download:
    CHECK_EVERY = 5
    MAX_WORKER_THREADS = 5

    def __init__(self, downloader, login, event_loop):
        self.event_loop = event_loop
        self.torrent_downloader = downloader(login, self.event_loop)

        self.shutdown = Value('b')
        self.downloads = Queue()

        self.transfers = []
        self.process_update_transfers = Process(target=self._update_transfers)
        self.process_update_transfers.start()

    def close(self):
        self.shutdown = True
        self.process_update_transfers.join(2)
        self.torrent_downloader.close()

    def _update_transfers(self):
        while not self.shutdown:
            future = asyncio.run_coroutine_threadsafe(self.torrent_downloader.get_transfers(), self.event_loop)
            self.transfers = future.result()
            time.sleep(self.CHECK_EVERY)

    async def download(self, information):
        logging.info('Downloading {}...'.format(information.show.name))

        await self._start_torrenting(information)

        worker_processes = []
        for _ in range(self.MAX_WORKER_THREADS):
            proc_ = TorrentDownloadWorker(self.downloads, self.shutdown, self.transfers, self.event_loop)
            proc_.start()
            worker_processes.append(proc_)

        [proc_.join() for proc_ in worker_processes]
        self.close()

    async def _start_torrenting(self, information):
        logging.info('Start torrenting {}...'.format(information.show.name))

        upload_ids = []
        for torrent in information.torrents:
            if torrent is not None:
                upload = self._upload(torrent, upload_ids)
                if upload:
                    download = Download(information, torrent.episode, upload, self.torrent_downloader)
                    self.downloads.put(download)

    async def _upload(self, torrent, upload_ids):
        for link in torrent.links:
            upload_ = await self.torrent_downloader.upload(link)
            if upload_:
                if upload_.id not in upload_ids:
                    upload_ids.append(upload_.id)
                    return upload_
                logging.warning('Torrent "{}" for episode "{}" was a duplicate'.format(link, torrent.episode))

    def __bool__(self):
        return bool(self.torrent_downloader)


DOWNLOADERS = {'premiumize.me': PremiumizeMeAPI, 'default': PremiumizeMeAPI}


class Download:
    def __init__(self, information, episode, upload, downloader):
        self.information = information
        self.episode = episode
        self.downloader = downloader

        self.upload = upload
        self.transfer = None
