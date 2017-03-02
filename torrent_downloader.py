import asyncio

from premiumize_me_dl.premiumie_me_downloader import PremiumizeMeDownloader

DOWNLOADERS = {'premiumize.me': PremiumizeMeDownloader, 'default': PremiumizeMeDownloader}


class Torrent2Download:
    def __init__(self, downloader, login, download_directory):
        self.downloader_login = login
        self.download_directory = download_directory

        self.event_loop = asyncio.get_event_loop()
        self.active_downloads = []

        downloader_class = DOWNLOADERS.get(downloader) if downloader in DOWNLOADERS else DOWNLOADERS.get('default')
        self.torrent2download = downloader_class(self.download_directory, self.downloader_login)

    def download(self, torrent):
        self._start_download(torrent)

        if not self.event_loop.is_running():
            self._start()

    def _start_download(self, torrent):
        """ Starts the download and installs a callback to download it when finished """
        for link in torrent.download_links_behind:
            self.torrent2download.upload(link)
        for link in torrent.download_links_missing:
            self.torrent2download.upload(link)

        self.active_downloads.append(torrent)

    def _download_waiter(self):
        while len(self.active_downloads) > 0:
            pass
        self.event_loop.close()

    def _start(self):
        self.event_loop.run_until_complete(self._download_waiter())
