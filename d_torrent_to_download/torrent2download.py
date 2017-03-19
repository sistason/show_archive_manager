import asyncio
import logging
import time
from multiprocessing import Value, Queue, Process

from d_torrent_to_download.torrent_download_worker import TorrentDownloadWorker
from premiumize_me_dl.premiumize_me_api import PremiumizeMeAPI


class Torrent2Download:
    CHECK_EVERY = 5
    MAX_WORKER_THREADS = 5

    def __init__(self, downloader, login, download_directory, event_loop):
        super().__init__()

        self.download_directory = download_directory

        self.event_loop = event_loop

        self.shutdown = Value('b')
        self.downloads = Queue()

        downloader_class = DOWNLOADERS.get(downloader) if downloader in DOWNLOADERS else DOWNLOADERS.get('default')
        self.torrent2download = downloader_class(login, self.event_loop)

        self.upload_ids = []
        self.transfers = []
        self.process_update_transfers = Process(target=self._update_transfers)
        self.process_update_transfers.start()

    def close(self):
        self.shutdown = True
        self.process_update_transfers.join(2)
        self.torrent2download.close()

    def _update_transfers(self):
        while not self.shutdown:
            future = asyncio.ensure_future(self.torrent2download.get_transfers())
            self.event_loop.run_until_complete(future)
            self.transfers = future.result()
            time.sleep(self.CHECK_EVERY)

    def download(self, show_download):
        logging.info('Downloading {}...'.format(show_download.status.show.name))

        self.event_loop.run_until_complete(self._start_torrenting(show_download))

        worker_processes = []
        for _ in range(self.MAX_WORKER_THREADS):
            proc_ = TorrentDownloadWorker(self.downloads, self.shutdown, self.transfers, self.event_loop)
            proc_.start()
            worker_processes.append(proc_)

        [proc_.join() for proc_ in worker_processes]
        self.close()

    async def _start_torrenting(self, show_download):
        logging.info('Start torrenting {}...'.format(show_download.status.show.name))

        for torrent in show_download.torrents_behind+show_download.torrents_missing:
            if torrent is None:
                continue
            for link in torrent.links:
                upload_ = await self.torrent2download.upload(link)
                if upload_:
                    if upload_.id not in self.upload_ids:
                        self.upload_ids.append(upload_.id)
                        download = Download(show_download.status.show, torrent.episode, upload_,
                                            self.torrent2download, self.download_directory)
                        self.downloads.put(download)
                        break
                    logging.warning('Torrent "{}" for episode "{}" was a duplicate, '
                                    'possibly bad downloads, check the downloads!'.format(link, torrent.episode))

    def __bool__(self):
        return bool(self.torrent2download)


DOWNLOADERS = {'premiumize.me': PremiumizeMeAPI, 'default': PremiumizeMeAPI}


class Download:
    def __init__(self, show, episode, upload, downloader, download_dir):
        self.show = show
        self.episode = episode
        self.downloader = downloader
        self.download_directory = download_dir

        self.upload = upload
        self.transfer = None