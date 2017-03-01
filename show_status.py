
import re
import os
import shutil
import logging

from thetvdb_api import Season, Episode


class ShowStatus:
    def __init__(self, show, dir):
        self.show = show
        self.download_directory = dir
        self.episodes_behind = None
        self.episode_holes = None

    def analyse(self):
        current_episode = self._get_current_episode()
        self.episodes_behind = self._get_episodes_behind(current_episode)
        self.episode_holes = self._get_show_holes()

    def _get_episodes_behind(self, current_episode):
        episodes_to_get = self.show.get_episodes_since(current_episode.date)
        # use <= and remove, instead of <, so multiple episodes on the same day do not get skipped
        episodes_to_get.remove(current_episode)
        return episodes_to_get

    def _get_current_episode(self):
        show_directory = os.path.join(self.download_directory, self.show.name)
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(self.show.name))
            return

        s1 = list(self.show.seasons.values())[0]
        seasons = [s1.get_season_from_string(s) for s in os.listdir(show_directory)]
        newest_season = self.show.seasons.get(max(seasons), self.show.get(max(self.show.keys())))

        return max(self._get_episodes_in_season_directory(newest_season, show_directory),
                   key=lambda e: e.episode)

    def _get_show_holes(self):
        missing_episodes = []
        show_directory = os.path.join(self.download_directory, self.show.name)
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(self.show.name))

        for season_nr, season in self.show.seasons.items():
            episodes_in_dir = self._get_episodes_in_season_directory(season, show_directory)
            [missing_episodes.append(ep) for ep in season.episodes if ep not in episodes_in_dir]

        return missing_episodes

    @staticmethod
    def _get_episodes_in_season_directory(season, show_directory):
        season_directory = os.path.join(show_directory, str(season))
        episodes = os.listdir(season_directory) if os.path.exists(season_directory) else []

        return [episode for episode in season.get_aired_episodes()
                if [e for e in episodes if episode.get_regex().search(e)]]

    def __str__(self):
        return 'The newest available episode for show "{}" is {}, but there are {} missing episodes'.format(
            self.show.name, self.current_episode, len(self.episode_holes))


class Show2Status:
    def __init__(self, download_directory):
        self.download_directory = download_directory

    def analyse(self, tvdb_show):
        show_status = ShowStatus(tvdb_show, self.download_directory)
        show_status.analyse()

        return show_status