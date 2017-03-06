import asyncio
from threading import Thread

from premiumize_me_dl.premiumie_me_downloader import PremiumizeMeDownloader


DOWNLOADERS = {'premiumize.me': PremiumizeMeDownloader, 'default': PremiumizeMeDownloader}


class Torrent2Download(Thread):
    def __init__(self, downloader, login, download_directory):
        super().__init__()
        self.downloader_login = login
        self.download_directory = download_directory

        self.event_loop = None
        self.download_queue = asyncio.Queue()

        downloader_class = DOWNLOADERS.get(downloader) if downloader in DOWNLOADERS else DOWNLOADERS.get('default')
        self.torrent2download = downloader_class(self.download_directory, self.downloader_login, self.event_loop)

    def download(self, show_downloads):
        # Enqueue torrents
        for sdl in show_downloads:
            self.download_queue.put_nowait(sdl)

        self.start()

    def run(self):
        self.event_loop = asyncio.get_event_loop()
        # asyncio.set_event_loop(self.event_loop) # Evtl nötig
        self.event_loop.run_until_complete(self._downloader())
        self.event_loop.close()

    async def _start_download(self, show_download):
        """ Starts the download and installs a callback to download it when finished """
        for link in show_download.download_links_behind:
            self.torrent2download.upload(link)
        for link in show_download.download_links_missing:
            self.torrent2download.upload(link)

        self.download_queue.put_nowait(show_download)

    async def _wait_download(self, downloader_id):
        ...

    async def _download(self, show_download, downloader_id):
        ...

    async def _cleanup(self, downloader_id):
        ...

    async def _downloader(self):
        while not self.download_queue.empty():
            show_download = await self.download_queue.get()
            downloader_id = await self._start_download(show_download)
            await self._wait_download(downloader_id)
            await self._download(show_download, downloader_id)
            await self._cleanup(downloader_id)


if __name__ == '__main__':
    from show_torrenter import ShowDownload
    t2d = Torrent2Download('premiumize.me', '../premiumize_me_dl/auth.txt', '.')
    show = ShowDownload()
    t2d.download()