#!/usr/bin/env python3
import os
import asyncio
import logging
from multiprocessing import Process

from a_argument_to_show.argument_to_show import Argument2Show
from b_show_to_status.show2status import Show2Status
from c_status_to_torrent.status2torrent import QUALITY_REGEX, Status2Torrent, GRABBER
from d_torrent_to_download.torrent2download import Torrent2Download, DOWNLOADERS


class ShowManager:
    MAX_MAIN_PROCESSES = 16

    def __init__(self, download_directory, auth, update_missing=False,
                 quality=None, torrent_site='', downloader=None):
        self.download_directory = download_directory
        self.event_loop = asyncio.get_event_loop()

        self.arg2show = Argument2Show()
        self.show2status = Show2Status(download_directory)
        self.status2torrent = Status2Torrent(torrent_site, quality, update_missing=update_missing)
        self.torrent2download = Torrent2Download(downloader, auth, download_directory,
                                                 self.event_loop)

    def _check_init(self):
        return bool(self.arg2show and self.show2status and self.status2torrent and self.torrent2download)

    def manage(self, show_arguments):
        if not self._check_init():
            logging.error('Initial setup of all components not possible, aborting...')
            return

        if not show_arguments:
            show_arguments = self.get_shows_from_directory()

        process_list = []
        for show in show_arguments:
            proc_ = Process(target=self._workflow, args=(show,))
            proc_.start()
            process_list.append(proc_)

        [proc_.join() for proc_ in process_list]
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

    def get_shows_from_directory(self):
        return [listing for listing in os.listdir(self.download_directory) if path.isdir(listing)]


if __name__ == '__main__':
    import argparse
    from os import path, access, W_OK, R_OK

    def argcheck_dir(string):
        if path.isdir(string) and access(string, W_OK) and access(string, R_OK):
            return path.abspath(string)
        raise argparse.ArgumentTypeError('{} is no directory or isn\'t writeable'.format(string))

    argparser = argparse.ArgumentParser(description="Manage your regular shows.")
    argparser.add_argument('shows', nargs='*', type=str,
                           help='Manage these shows.')
    argparser.add_argument('download_directory', type=argcheck_dir, default='.',
                           help='Set the directory to sort the file(s) into.')
    argparser.add_argument('-a', '--auth', type=str, required=True,
                           help="Either 'user:password' or a path to a pw-file with that format (for premiumize.me)")
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

    sm = ShowManager(args.download_directory, args.auth,
                     update_missing=args.update_missing, quality=quality_dict, torrent_site=args.torrent_site,
                     downloader=args.downloader)
    sm.manage(args.shows)
