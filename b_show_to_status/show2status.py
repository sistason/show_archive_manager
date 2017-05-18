import logging
import os

from b_show_to_status.show_status import Status


class Show2Status:
    def __init__(self, update_missing):
        self.update_missing = update_missing

    def analyse(self, information):
        show_, dl_directory_ = information.show, information.download_directory
        logging.debug('Getting status of show "{}" on disk...'.format(show_.name))

        seasons_missing, episodes_missing = [], []
        seasons_to_check = show_.seasons.values() if self.update_missing else [show_.seasons.get(max(show_.seasons))]
        for season_ in seasons_to_check:
            if season_.number == 0:
                continue
            episodes = self._get_episodes_missing(show_, season_, dl_directory_)
            if len(episodes) > 0.9*len(season_.episodes):
                seasons_missing.append(season_)
            else:
                episodes_missing.extend(episodes)

        status = Status(seasons_missing, episodes_missing)
        logging.info('{} {}'.format(information.show.name, status))
        return status

    def _get_episodes_missing(self, show, season, directory):
        show_directory = os.path.join(directory, show.get_storage_name())
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(show.name))

        episodes_in_dir = self._get_episodes_in_season_directory(season, show_directory)
        if not episodes_in_dir:
            logging.debug('Directory for season {} does not exist!'.format(season.number))

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
