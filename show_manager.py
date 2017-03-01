#!/usr/bin/env python3
import logging
import os

from argument_to_show import Argument2Show
from show_status import Show2Status
from show_torrenter import Status2Torrent

QUALITIES=['480p', '720p', '1080p']
ENCODER=['x264', 'x265', 'xvid']


class ShowManager:
    def __init__(self, download_directory, auth, cleanup_premiumize=True, update_missing=False, quality={}):
        self.cleanup_premiumize = cleanup_premiumize
        self.update_missing = update_missing
        self.download_dir = download_directory
        self.quality = quality

        self.premiumize_login = {}
        self._store_auth(auth)

        self.shows = []

    def manage(self, shows):
        tvdb_shows = self._parse_arguments(shows)
        show_states = self._get_show_states(tvdb_shows)
        show_torrents = self._get_torrents(show_states)
        print([str(s) for s in show_states])

    @staticmethod
    def _parse_arguments(shows):
        arg2show = Argument2Show()
        return [arg2show.argument2show(s) for s in shows]

    def _get_show_states(self, tvdb_shows):
        show2status = Show2Status(self.download_dir)
        return [show2status.analyse(s) for s in tvdb_shows]

    def _get_torrents(self, show_states):
        status2torrent = Status2Torrent(self.quality, update_missing=self.update_missing)
        return [status2torrent.get_torrent(s) for s in show_states]

    def _store_auth(self, auth):
        if auth and os.path.exists(auth):
            with open(auth, 'r') as f:
                auth = f.read()

        if not (auth and ':' in auth):
            logging.error('No ":" found in authentication information, login not possible!')
            return

        username, password = auth.strip().split(':')
        self.premiumize_login = {'customer_id': username, 'pin': password}


if __name__ == '__main__':
    import argparse
    from os import path, access, W_OK, R_OK

    quality_choices = []
    [[quality_choices.append(' '.join([q, e])) for e in ENCODER] for q in QUALITIES]

    def argcheck_dir(string):
        if path.isdir(string) and access(string, W_OK) and access(string, R_OK):
            return path.abspath(string)
        raise argparse.ArgumentTypeError('{} is no directory or isn\'t writeable'.format(string))

    argparser = argparse.ArgumentParser(description="Manage your regular shows.")
    argparser.add_argument('shows', nargs='+', type=str,
                           help='Manage these shows.')
    argparser.add_argument('download_directory', type=argcheck_dir, default='.',
                           help='Set the directory to sort the file(s) into.')
    argparser.add_argument('-a', '--auth', type=str, required=True,
                           help="Either 'user:password' or a path to a pw-file with that format (for premiumize.me)")
    argparser.add_argument('-c', '--cleanup_premiumize', action="store_true",
                           help="Delete files from My Files after successful download")
    argparser.add_argument('-u', '--update_missing', action="store_true",
                           help="update shows, check if there are missing episode and download them")
    argparser.add_argument('-q', '--quality', type=str, default='720p h264', choices=quality_choices,
                           help="Either 'user:password' or a path to a pw-file with that format (for premiumize.me)")

    args = argparser.parse_args()
    quality, encoder = args.quality.split(' ')
    quality_dict = {'quality': quality, 'encoder': encoder}

    logging.basicConfig(format='%(message)s',
                        level=logging.INFO)

    sm = ShowManager(args.download_directory, args.auth, cleanup_premiumize=args.cleanup_premiumize,
                     update_missing=args.update_missing, quality=quality_dict)
    sm.manage(args.shows)


