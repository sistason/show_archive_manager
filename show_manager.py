#!/usr/bin/env python3
import asyncio
import logging
from multiprocessing import Pool

from argument_to_show import Argument2Show
from show_status import Show2Status
from show_torrenter import QUALITY_REGEX, Status2Torrent
from torrent_downloader import Torrent2Download, DOWNLOADERS


class ShowManager:
    MAX_MAIN_PROCESSES = 16

    def __init__(self, download_directory, auth, cleanup_premiumize=True, update_missing=False,
                 quality=None, torrent_site='', downloader=None):
        self.event_loop = asyncio.get_event_loop()

        self.arg2show = Argument2Show()
        self.show2status = Show2Status(download_directory)
        self.status2torrent = Status2Torrent(torrent_site, quality, update_missing=update_missing)
        self.torrent2download = Torrent2Download(downloader, auth, download_directory,
                                                 self.event_loop, cleanup=cleanup_premiumize)

    def _check_init(self):
        return bool(self.arg2show and self.show2status and self.status2torrent and self.torrent2download)

    def manage(self, shows):
        if not self._check_init():
            logging.error('Initial setup of all components not possible, aborting...')
            return

        process_pool = Pool(self.MAX_MAIN_PROCESSES)
        process_pool.map(self._workflow, shows)
        self.close()

    def _workflow(self, show_argument):
        tvdb_show = self.arg2show.argument2show(show_argument)
        logging.debug('Found show "{}" for argument "{}"'.format(tvdb_show, show_argument))
        if not tvdb_show:
            return
        show_state = self.show2status.analyse(tvdb_show)
        if not show_state:
            return
        show_downloads = self.status2torrent.get_torrents(show_state)
        if not show_downloads:
            return
        self.torrent2download.download(show_downloads)

    def close(self):
        self.status2torrent.torrent_grabber.close()
        self.torrent2download.close()
        self.event_loop.close()

if __name__ == '__main__':
    import argparse
    from os import path, access, W_OK, R_OK

    def argcheck_dir(string):
        if path.isdir(string) and access(string, W_OK) and access(string, R_OK):
            return path.abspath(string)
        raise argparse.ArgumentTypeError('{} is no directory or isn\'t writeable'.format(string))

    argparser = argparse.ArgumentParser(description="Manage your regular shows.")
    argparser.add_argument('shows', nargs='+', type=str,  # TODO: nargs="*", look at dl_dir which shows to manage
                           help='Manage these shows.')
    argparser.add_argument('download_directory', type=argcheck_dir, default='.',
                           help='Set the directory to sort the file(s) into.')
    argparser.add_argument('-a', '--auth', type=str, required=True,
                           help="Either 'user:password' or a path to a pw-file with that format (for premiumize.me)")
    argparser.add_argument('-c', '--cleanup_premiumize', action="store_true",
                           help="Delete files from My Files after successful download")
    argparser.add_argument('-u', '--update_missing', action="store_true",
                           help="update shows, check if there are missing episode and download them")
    argparser.add_argument('-q', '--quality', type=str, choices=QUALITY_REGEX.get('quality').keys(),
                           help="Choose the quality of the episodes to download")
    argparser.add_argument('-e', '--encoder', type=str, choices=QUALITY_REGEX.get('encoder').keys(),
                           help="Choose the encoder of the episodes to download")
    argparser.add_argument('-t', '--torrent_site', type=str, default='piratebay', choices=GRABBER.keys(),
                           help="Choose the encoder of the episodes to download")
    argparser.add_argument('-d', '--downloader', type=str, default='premiumize.me', choices=DOWNLOADERS.keys(),
                           help="Choose the encoder of the episodes to download")

    args = argparser.parse_args()
    quality_dict = {'quality': args.quality, 'encoder': args.encoder}

    logging.basicConfig(format='%(message)s',
                        level=logging.DEBUG)

    sm = ShowManager(args.download_directory, args.auth, cleanup_premiumize=args.cleanup_premiumize,
                     update_missing=args.update_missing, quality=quality_dict, torrent_site=args.torrent_site,
                     downloader=args.downloader)
    sm.manage(args.shows)
