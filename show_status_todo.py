
import re
import os
import shutil
import logging
from thetvdb_api import TVDBShow


class ShowStatus:
    def __init__(self, show, dir):
        self.show = show
        self.download_directory = dir
        self.current_episode = None
        self.episode_holes = None

    def analyse(self):
        self.current_episode = self.show.get_newest_episode()
        self.episode_holes = self._get_episode_holes()

    def _get_episode_holes(self):
        show_directory = os.path.join(self.download_directory, self.show.name)
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(self.show.name))
            return


        return []


class Show2Status:
    def __init__(self, download_directory):
        self.download_directory = download_directory

    def analyse(self, imdb_show):
        show_status = ShowStatus(imdb_show, self.download_directory)
        show_status.analyse()

        return show_status