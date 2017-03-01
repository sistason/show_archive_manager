#!/usr/bin/env python3
import logging
import os

from argument_to_show import Argument2Show
from show_status_todo import Show2Status


class ShowManager:
    def __init__(self, shows, download_directory, auth, cleanup_premiumize=True):
        self.cleanup_premiumize = cleanup_premiumize
        self.download_dir = download_directory

        self.premiumize_login = {}
        self._store_auth(auth)

        imdb_shows = self._parse_arguments(shows)
        self.shows = self._get_show_status(imdb_shows)

    @staticmethod
    def _parse_arguments(shows):
        arg2show = Argument2Show()
        return [arg2show.argument2show(s) for s in shows]

    def _get_show_status(self, imdb_shows):
        show2status = Show2Status(self.download_dir)
        return [show2status.analyse(s) for s in imdb_shows]

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

    args = argparser.parse_args()

    logging.basicConfig(format='%(message)s',
                        level=logging.INFO)

    sm = ShowManager(args.shows, args.download_directory, args.auth,
                                cleanup_premiumize=args.cleanup_premiumize)


