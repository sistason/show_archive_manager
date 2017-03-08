import asyncio
import time
import logging

from premiumize_me_dl.premiumize_me_download import PremiumizeMeDownloader


DOWNLOADERS = {'premiumize.me': PremiumizeMeDownloader, 'default': PremiumizeMeDownloader}


class Torrent2Download:
    CHECK_EVERY = 5

    def __init__(self, downloader, login, download_directory, event_loop=None):
        super().__init__()
        self.downloader_login = login
        self.download_directory = download_directory

        self.shutdown = False
        self.event_loop = event_loop
        self.download_queue = asyncio.Queue()
        self.transfers = []

        downloader_class = DOWNLOADERS.get(downloader) if downloader in DOWNLOADERS else DOWNLOADERS.get('default')
        self.torrent2download = downloader_class(self.download_directory, self.downloader_login, self.event_loop)

    def close(self):
        self.shutdown = True
        self.torrent2download.close()

    def enqueue(self, show_download_):
        self.download_queue.put_nowait(show_download_)

    async def download(self):
        await self._update_transfers()

        while not self.download_queue.empty():
            show_download_ = await self.download_queue.get()
            if show_download_:
                self._download_show(show_download_)

            self.download_queue.task_done()

        await self.download_queue.join()
        self.close()

    async def _update_transfers(self):
        self.transfers = await self.torrent2download.get_transfers()
        if not self.shutdown:
            self.event_loop.call_later(self.CHECK_EVERY, self._update_transfers())

    async def _download_show(self, show_download_):
        uploads = await self._start_torrenting_links(show_download_)
        for upload in uploads:
            await self._wait_torrenting(upload)
            await self._download(show_download_, upload)
            await self._cleanup(upload)

    async def _start_torrenting_links(self, show_download):
        logging.info('Start torrenting {}...'.format(show_download))

        behind_uploads = await self._upload(show_download.download_links_behind)
        missing_uploads = await self._upload(show_download.download_links_missing)

        return behind_uploads + missing_uploads

    async def _upload(self, links_to_upload):
        uploads_ = []
        for link in links_to_upload:
            upload_ = await self.torrent2download.upload(link)
            if upload_.worked():
                uploads_.append(upload_)
        return uploads_

    async def _wait_torrenting(self, upload):
        logging.info('Wait while torrenting {}...'.format(upload.name))

        while True:
            transfer = self._get_torrent_transfer(upload)
            if not transfer.is_running():
                if transfer.status == 'error':
                    logging.error('Error torrenting {}!'.format(upload.name))
                break
            await asyncio.sleep(self.CHECK_EVERY/2)

        logging.info('Finished torrenting {}'.format(upload.name))

    def _get_torrent_transfer(self, upload):
        for transfer in self.transfers:
            if transfer.id == upload.id:
                return transfer

    async def _download(self, show_download, upload):
        print('downloading...')
        ...

    async def _cleanup(self, upload):
        logging.info('Cleaning up {}'.format(upload.name))

        await self.torrent2download.delete(upload)


if __name__ == '__main__':
    from show_torrenter import ShowDownload
    from show_status import ShowStatus
    from thetvdb_api import TheTVDBAPI

    api = TheTVDBAPI()
    show = api.get_show_by_imdb_id('tt4016454')
    show_download = ShowDownload(ShowStatus(show, '.'))
    show_download.download_links_behind = [
        "https://thepiratebay.org/torrent/17226840/Supernatural.S12E14.HDTV.x264-LOL[ettv]"]
    show_download.download_links_missing = []

    event_loop = asyncio.get_event_loop()

    t2d = Torrent2Download('premiumize.me', '../premiumize_me_dl/auth.txt', '.', event_loop=event_loop)
    t2d.enqueue(show_download)

    try:
        event_loop.run_until_complete(t2d.download())
    except KeyboardInterrupt:
        pass
    finally:
        t2d.close()

    event_loop.close()