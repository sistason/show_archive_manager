import logging
import os

from b_show_to_status.show_status import Status


class Show2Status:
    def __init__(self, update_missing):
        self.update_missing = update_missing

    def analyse(self, information):
        logging.debug('Getting status of show "{}" on disk...'.format(information.show.name))

        behind = self._get_episodes_behind(information.show, information.download_directory)
        if self.update_missing:
            missing = self._get_episodes_missing(information.show, information.download_directory)
            [missing.remove(behind) for behind in behind]
        else:
            missing = []

        return Status(behind, missing)

    def _get_episodes_behind(self, show, directory):
        latest_season = show.seasons.get(max(show.seasons.keys()))

        show_directory = os.path.join(directory, show.get_storage_name())
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(show.name))
            return latest_season.episodes if latest_season else []

        seasons = [latest_season.get_season_from_string(s) for s in os.listdir(show_directory)
                   if os.path.isdir(os.path.join(show_directory, s))]
        newest_season = show.seasons.get(max(seasons, default=-1), latest_season)

        episodes_available = self._get_episodes_in_season_directory(newest_season, show_directory)
        if not episodes_available:
            logging.warning('Show "{}"s latest season-directory is empty'.format(show.name))
            return newest_season.episodes

        current_episode = max(episodes_available, key=lambda e: e.episode)
        episodes_to_get = show.get_episodes_since(current_episode.date)
        # use <= and remove, instead of <, so multiple episodes on the same day do not get skipped
        episodes_to_get.remove(current_episode)
        logging.debug('{} has current_episode {} and needs to get {}'.format(show.name, current_episode,
                                                                             list(map(str, episodes_to_get))))
        return episodes_to_get

    def _get_episodes_missing(self, show, directory):
        missing_episodes = []
        show_directory = os.path.join(directory, show.get_storage_name())
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(show.name))

        logging.debug('{} has missing episodes:'.format(show.name))
        for season_nr, season in show.seasons.items():
            episodes_in_dir = self._get_episodes_in_season_directory(season, show_directory)
            missing_ = [ep for ep in season.get_aired_episodes()
                        if ep not in episodes_in_dir]
            missing_episodes.extend(missing_)
            logging.debug('  Season {}: {}'.format(season_nr, list(map(str, missing_))))

        return missing_episodes

    @staticmethod
    def _get_episodes_in_season_directory(season, show_directory):
        season_directory = os.path.join(show_directory, str(season))
        episodes = os.listdir(season_directory) if os.path.exists(season_directory) else []

        return [episode for episode in season.get_aired_episodes()
                if [e for e in episodes if episode.get_regex().search(e)]]

    def __bool__(self):
        return True
