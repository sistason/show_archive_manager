import asyncio
import logging
import os
import time
from multiprocessing import Process, Queue, Value

from premiumize_me_dl.premiumize_me_api import PremiumizeMeAPI

DOWNLOADERS = {'premiumize.me': PremiumizeMeAPI, 'default': PremiumizeMeAPI}


class Download:
    def __init__(self, show, episode, upload, downloader, download_dir):
        self.show = show
        self.episode = episode
        self.downloader = downloader
        self.download_directory = download_dir

        self.upload = upload
        self.transfer = None


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


class TorrentDownloadWorker(Process):
    def __init__(self, downloads, shutdown, transfers, event_loop):
        super().__init__()
        self.downloads_queue = downloads
        self.shutdown = shutdown
        self.transfers = transfers
        self.event_loop = event_loop

    def run(self):
        while not self.shutdown or self.downloads_queue.empty():
            download = self.downloads_queue.get()
            if self._is_transfer_ready_to_download(download):
                self._download(download)
                self._cleanup(download)

    def _is_transfer_ready_to_download(self, download):
        download.transfer = self._get_torrent_transfer(download.upload)
        if download.transfer is None:
            logging.error('Error torrenting {}, torrent not found anymore!'.format(download.name))
            return False

        if download.transfer.is_running():
            self.downloads_queue.put(download)
            return False

        if download.transfer.status == 'error':
            logging.error('Error torrenting {}: {}'.format(download.transfer.name, download.transfer.message))
            return False

        return True

    def _get_torrent_transfer(self, upload):
        for transfer in self.transfers:
            if transfer.id == upload.id:
                return transfer

    def _download(self, download):
        episode_directory = os.path.join(download.download_directory, str(download.show.name),
                                         str(download.show.seasons.get(download.episode.season)))
        os.makedirs(episode_directory, exist_ok=True)

        future = asyncio.ensure_future(download.downloader.download_file(download.transfer,
                                                                             download_directory=episode_directory))
        self.event_loop.run_until_complete(future)
        return future.result()

    def _cleanup(self, download):
        logging.info('Cleaning up {}'.format(download.upload.name))
        self.event_loop.run_until_complete(download.downloader.delete(download.upload))


if __name__ == '__main__':
    from show_torrenter import ShowDownload, Torrent
    from show_status import ShowStatus
    from thetvdb_api import TheTVDBAPI

    logging.basicConfig(format='%(message)s',
                        level=logging.INFO)

    api = TheTVDBAPI()
    show_ = api.get_show_by_imdb_id('tt4016454')
    show_download_ = ShowDownload(ShowStatus(show_, '.'))
    show_download_.torrents_behind = [Torrent(show_.episodes[10], [
        "https://thepiratebay.org/torrent/17226840/Supernatural.S12E14.HDTV.x264-LOL[ettv]"])]
    show_download_.torrents_missing = []

    event_loop_ = asyncio.get_event_loop()

    t2d = Torrent2Download('premiumize.me', '../premiumize_me_dl/auth.txt', '.', event_loop=event_loop_)
    try:
        event_loop_.run_until_complete(t2d.download(show_download_))
    except KeyboardInterrupt:
        pass
    finally:
        t2d.close()

    event_loop_.close()
