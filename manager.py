#!/usr/bin/env python3
import asyncio
import logging
import os

from a_argument_to_show.argument_to_show import Argument2Show
from b_show_to_status.show2status import Show2Status
from c_status_to_torrent.status2torrent import QUALITY_REGEX, Status2Torrent
from d_torrent_to_download.torrent2download import Torrent2Download


class Information:
    def __init__(self, download_directory):
        self.download_directory = download_directory
        self.show = None
        self.status = None
        self.torrents = []


class ShowManager:
    def __init__(self, download_directory, auth, update_missing=False,
                 quality=None):
        self.download_directory = download_directory
        self.event_loop = asyncio.get_event_loop()

        self.arg2show = Argument2Show()
        self.show2status = Show2Status(update_missing)
        self.status2torrent = Status2Torrent(quality, self.event_loop)
        self.torrent2download = Torrent2Download(auth, self.event_loop)

    def _check_init(self):
        return bool(self.arg2show and self.show2status and self.status2torrent and self.torrent2download)

    def manage(self, show_arguments):
        if not self._check_init():
            logging.error('Initial setup of all components not possible, aborting...')
            return

        if not show_arguments:
            show_arguments = self.get_shows_from_directory()

        # Convert Arguments to shows synchronous, as they might require user input and are fundamental.
        shows = []
        for arg in show_arguments:
            s_ = self.arg2show.argument2show(arg)
            if s_ is not None:
                shows.append(s_)

        tasks = asyncio.gather(*[self._workflow(show) for show in shows])
        try:
            self.event_loop.run_until_complete(tasks)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print('exception!')
            print(e)
            raise e
        finally:
            self.close()

    async def _workflow(self, show):
        show_infos = Information(self.download_directory)
        show_infos.show = show

        show_infos.status = self.show2status.analyse(show_infos)
        if not len(show_infos.status):
            return
        show_infos_remaining = await self.torrent2download.download_from_cache(show_infos)
        show_infos_remaining.torrents = await self.status2torrent.get_torrents(show_infos_remaining)
        if not show_infos_remaining.torrents and self.torrent2download.downloads_queue.empty():
            return
        await self.torrent2download.download(show_infos_remaining)

    def close(self):
        self.event_loop.run_until_complete(self.status2torrent.torrent_grabber.close())
        self.event_loop.run_until_complete(self.torrent2download.close())
        self.event_loop.close()

    def get_shows_from_directory(self):
        folder_name = os.path.dirname(self.download_directory)
        directory_imdb_id = self.arg2show.get_imdb_id(folder_name)
        if directory_imdb_id:
            # set the download_directory as ../, as we are in a season-directory apparently
            self.download_directory = os.path.join(self.download_directory, os.pardir)
            return [directory_imdb_id]

        return [listing for listing in os.listdir(self.download_directory)
                if os.path.isdir(os.path.join(self.download_directory, listing)) and not listing.startswith('#')]


if __name__ == '__main__':
    import argparse

    def argcheck_dir(string):
        if os.path.isdir(string) and os.access(string, os.W_OK) and os.access(string, os.R_OK):
            directory_path = os.path.abspath(string)
            if os.path.isdir(directory_path) and not directory_path.endswith('/'):
                directory_path += '/'
            return directory_path

        raise argparse.ArgumentTypeError('{} is no directory or isn\'t writeable'.format(string))


    argparser = argparse.ArgumentParser(description="Manage your tv-show directories")
    argparser.add_argument('shows', nargs='*', type=str,
                           help='Manage these shows or let free to get the shows automatically from download_directory')
    argparser.add_argument('download_directory', type=argcheck_dir, default='.',
                           help='Set the directory to sort the file(s) into.')
    argparser.add_argument('-a', '--auth', type=str,
                           help="Either 'user:password' or a path to a pw-file with that format (for premiumize.me)")
    argparser.add_argument('-u', '--update_missing', action="store_true",
                           help="update (download) missing episodes/seasons")
    argparser.add_argument('-q', '--quality', type=str, choices=QUALITY_REGEX.get('quality').keys(),
                           help="Choose the quality of the episodes to download", default='720')
    argparser.add_argument('-e', '--encoder', type=str, choices=QUALITY_REGEX.get('encoder').keys(),
                           help="Choose the encoder of the episodes to download", default='264')
    argparser.add_argument('-v', '--verbose', action='store_true')

    args = argparser.parse_args()
    quality_dict = {'quality': args.quality, 'encoder': args.encoder}

    logging.basicConfig(format='%(message)s',
                        level=logging.DEBUG if args.verbose else logging.INFO)

    sm = ShowManager(args.download_directory, args.auth, update_missing=args.update_missing,
                     quality=quality_dict)
    sm.manage(args.shows)
