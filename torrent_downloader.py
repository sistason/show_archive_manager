import os
import asyncio
import logging

from premiumize_me_dl.premiumize_me_api import PremiumizeMeAPI

DOWNLOADERS = {'premiumize.me': PremiumizeMeAPI, 'default': PremiumizeMeAPI}


class Download:
    def __init__(self, show, episode, upload):
        self.show = show
        self.episode = episode
        self.upload = upload
        self.transfer = None


class Torrent2Download:
    CHECK_EVERY = 5

    def __init__(self, downloader, login, download_directory, event_loop, cleanup=True):
        super().__init__()

        self.download_directory = download_directory
        self.cleanup = cleanup

        self.shutdown = False
        self.event_loop = event_loop
        self.transfers = []
        self.upload_ids = []

        downloader_class = DOWNLOADERS.get(downloader) if downloader in DOWNLOADERS else DOWNLOADERS.get('default')
        self.torrent2download = downloader_class(login, self.event_loop)

    def close(self):
        self.shutdown = True
        self.torrent2download.close()
        import time
        time.sleep(2)

    async def download(self, show_download):
        asyncio.ensure_future(self._update_transfers())
        await self._download_show(show_download)
        await asyncio.sleep(2)

    async def _update_transfers(self):
        if self.shutdown:
            return
        self.transfers = await self.torrent2download.get_transfers()
        await asyncio.sleep(self.CHECK_EVERY)
        await self._update_transfers()

    async def _download_show(self, show_download):
        logging.info('Downloading {}...'.format(show_download.status.show.name))

        downloads = await self._start_torrenting(show_download)
        await asyncio.gather(*[self.wait_and_download(download) for download in downloads])

    async def wait_and_download(self, download):
        transfer = await self._wait_torrenting(download.upload)
        if transfer is not None and await self._download(download, transfer):
            await self._cleanup(download.upload)

    async def _start_torrenting(self, show_download):
        logging.info('Start torrenting {}...'.format(show_download.status.show.name))

        downloads = []
        for torrent in show_download.torrents_behind+show_download.torrents_missing:
            if torrent is None:
                continue
            for link in torrent.links:
                upload_ = await self.torrent2download.upload(link)
                if upload_:
                    if upload_.id not in self.upload_ids:
                        self.upload_ids.append(upload_.id)
                        downloads.append(Download(show_download.status.show, torrent.episode, upload_))
                        break
                    logging.warning('Torrent "{}" for episode "{}" was a duplicate, '
                                    'possibly bad downloads, check the downloads!'.format(link, torrent.episode))
        return downloads

    async def _wait_torrenting(self, upload):
        logging.info('Wait while torrenting {}...'.format(upload.name))
        transfer = None
        while True:
            if transfer is None:
                transfer = self._get_torrent_transfer(upload)
                if not transfer:
                    logging.error('Error torrenting {}, torrent not found anymore!'.format(upload.name))
                    return None

            if not transfer.is_running():
                if transfer.status == 'error':
                    logging.error('Error torrenting {}!'.format(transfer.name))
                logging.info('Finished torrenting {}'.format(transfer.name))
                return transfer

            await asyncio.sleep(self.CHECK_EVERY/2)

    def _get_torrent_transfer(self, upload):
        for transfer in self.transfers:
            print(upload.id, transfer.id, transfer)
            if transfer.id == upload.id:
                return transfer

    async def _download(self, download, transfer):
        episode_directory = os.path.join(self.download_directory, str(download.show.name),
                                         str(download.show.seasons.get(download.episode.season)))
        os.makedirs(episode_directory, exist_ok=True)

        return await self.torrent2download.download_file(transfer, download_directory=episode_directory)

    async def _cleanup(self, upload):
        logging.info('Cleaning up {}'.format(upload.name))
        if self.cleanup:
            await self.torrent2download.delete(upload)

    def __bool__(self):
        return bool(self.torrent2download)


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
