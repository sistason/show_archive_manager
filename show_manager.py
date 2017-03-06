#!/usr/bin/env python3
import logging
import os

from argument_to_show import Argument2Show
from show_status import Show2Status
from show_torrenter import QUALITY_REGEX, SITES
from torrent_downloader import Torrent2Download, DOWNLOADERS


class ShowManager:
    def __init__(self, download_directory, auth, cleanup_premiumize=True, update_missing=False,
                 quality=None, torrent_site=SITES.get('default'), downloader=None):
        self.cleanup_premiumize = cleanup_premiumize
        self.update_missing = update_missing
        self.download_directory = download_directory
        self.quality = quality if quality else None
        self.torrent_site = torrent_site
        self.downloader = downloader

        self.login = {}
        self._store_auth(auth)

    def manage(self, shows):
        tvdb_shows = self._parse_arguments(shows)
        show_states = self._get_show_states(tvdb_shows)
        show_downloads = self._get_torrents(show_states)
        self._download_torrents(show_downloads)

    @staticmethod
    def _parse_arguments(show_arguments):
        arg2show = Argument2Show()
        return [arg2show.argument2show(s) for s in show_arguments]

    def _get_show_states(self, tvdb_shows):
        show2status = Show2Status(self.download_directory)
        return [show2status.analyse(s) for s in tvdb_shows if s]

    def _get_torrents(self, show_states):
        torrent_site = SITES.get(self.torrent_site) if self.torrent_site in SITES else SITES.get('default')
        status2torrent = torrent_site(self.quality, update_missing=self.update_missing)
        return [status2torrent.get_torrent(s) for s in show_states]

    def _download_torrents(self, show_downloads):
        torrent2download = Torrent2Download(self.downloader, self.login, self.download_directory)
        torrent2download.download(show_downloads)
        return torrent2download.join()

    def _store_auth(self, auth):
        if auth and os.path.exists(auth):
            with open(auth, 'r') as f:
                auth = f.read()

        if not (auth and ':' in auth):
            logging.error('No ":" found in authentication information, login not possible!')
            return

        username, password = auth.strip().split(':')
        self.login = {'customer_id': username, 'pin': password}


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
    argparser.add_argument('-q', '--quality', type=str, default='720p', choices=QUALITY_REGEX.get('quality').keys(),
                           help="Choose the quality of the episodes to download")
    argparser.add_argument('-e', '--encoder', type=str, default='h264', choices=QUALITY_REGEX.get('encoder').keys(),
                           help="Choose the encoder of the episodes to download")
    argparser.add_argument('-t', '--torrent_site', type=str, default='piratebay', choices=SITES.keys(),
                           help="Choose the encoder of the episodes to download")
    argparser.add_argument('-d', '--downloader', type=str, default='premiumize.me', choices=DOWNLOADERS.keys(),
                           help="Choose the encoder of the episodes to download")

    args = argparser.parse_args()
    quality_dict = {'quality': args.quality, 'encoder': args.encoder}

    logging.basicConfig(format='%(message)s',
                        level=logging.INFO)

    sm = ShowManager(args.download_directory, args.auth, cleanup_premiumize=args.cleanup_premiumize,
                     update_missing=args.update_missing, quality=quality_dict, torrent_site=args.torrent_site,
                     downloader=args.downloader)
    sm.manage(args.shows)
