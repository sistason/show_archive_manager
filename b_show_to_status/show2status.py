import logging
import os

from b_show_to_status.show_status import Status


class Show2Status:
    def __init__(self, update_missing):
        self.update_missing = update_missing

    def analyse(self, information):
        show_, dl_directory_ = information.show, information.download_directory
        logging.debug('Getting status of show "{}" on disk...'.format(show_.name))

        latest_season = show_.seasons.get(max(show_.seasons.keys()))
        behind = self._get_episodes_missing(show_, latest_season, dl_directory_)

        if self.update_missing:
            missing = [self._get_episodes_missing(show_, season, dl_directory_) for season in show_.seasons.values()]
            [missing.remove(behind) for behind in behind if behind in missing]
        else:
            missing = []

        status = Status(behind, missing)
        logging.info('{} {}'.format(information.show.name, status))
        return status

    def _get_episodes_missing(self, show, season, directory):
        show_directory = os.path.join(directory, show.get_storage_name())
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(show.name))

        episodes_in_dir = self._get_episodes_in_season_directory(season, show_directory)
        if not episodes_in_dir:
            logging.warning('Directory for season {} does not exist!'.format(season.number))

        missing_ = [ep for ep in season.get_aired_episodes()
                    if ep not in episodes_in_dir]

        logging.debug('{} - Missing episodes of season {}: {}'.format(show, season.number, list(map(str, missing_))))
        return missing_

    @staticmethod
    def _get_episodes_in_season_directory(season, show_directory):
        season_directory = os.path.join(show_directory, str(season))
        episodes = os.listdir(season_directory) if os.path.exists(season_directory) else []

        return [episode for episode in season.get_aired_episodes()
                if [e for e in episodes if episode.get_regex().search(e)]]

    def __bool__(self):
        return True
