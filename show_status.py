import logging
import os


class ShowStatus:
    def __init__(self, show, download_directory):
        self.show = show
        self.download_directory = download_directory
        self.episodes_behind = None
        self.episodes_missing = None
        self.download_links = None

    def analyse(self):
        logging.debug('Getting status of show "{}" on disk...'.format(self.show.name))
        self.episodes_behind = self._get_episodes_behind()
        self.episodes_missing = self._get_episodes_missing()

    def _get_episodes_behind(self):
        show_directory = os.path.join(self.download_directory, self.show.name)
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(self.show.name))
            return []

        latest_season = self.show.seasons.get(max(self.show.seasons.keys()))
        seasons = [latest_season.get_season_from_string(s) for s in os.listdir(show_directory) if os.path.isdir(s)]

        newest_season = self.show.seasons.get(max(seasons, default=-1), latest_season)

        episodes_available = self._get_episodes_in_season_directory(newest_season, show_directory)
        if not episodes_available:
            logging.warning('Show "{}"s latest season-directory is empty'.format(self.show.name))
            return newest_season.episodes

        current_episode = max(episodes_available, key=lambda e: e.episode)
        episodes_to_get = self.show.get_episodes_since(current_episode.date)
        # use <= and remove, instead of <, so multiple episodes on the same day do not get skipped
        episodes_to_get.remove(current_episode)
        logging.debug('{} has current_episode {} and needs to get {}'.format(self.show.name, current_episode,
                                                                             list(map(str, episodes_to_get))))
        return episodes_to_get

    def _get_episodes_missing(self):
        missing_episodes = []
        show_directory = os.path.join(self.download_directory, self.show.name)
        if not os.path.exists(show_directory):
            logging.warning('Directory for show "{}" does not exist!'.format(self.show.name))

        logging.debug('{} has missing episodes:'.format(self.show.name))
        for season_nr, season in self.show.seasons.items():
            episodes_in_dir = self._get_episodes_in_season_directory(season, show_directory)
            missing_ = [ep for ep in season.get_aired_episodes()
                        if ep not in episodes_in_dir and ep not in self.episodes_behind]
            missing_episodes.extend(missing_)
            logging.debug('  Season {}: {}'.format(season_nr, list(map(str, missing_))))

        return missing_episodes

    @staticmethod
    def _get_episodes_in_season_directory(season, show_directory):
        season_directory = os.path.join(show_directory, str(season))
        episodes = os.listdir(season_directory) if os.path.exists(season_directory) else []

        return [episode for episode in season.get_aired_episodes()
                if [e for e in episodes if episode.get_regex().search(e)]]

    def __str__(self):
        behind_ = 'is {} episodes behind'.format(len(self.episodes_behind)) if self.episodes_behind else ''
        missing_ = 'has {} missing episodes'.format(len(self.episodes_missing)) if self.episodes_missing else ''

        return 'Show "{}" {}'.format(self.show.name, 'and '.join([i for i in (behind_, missing_) if i]))

    def __len__(self):
        return len(self.episodes_behind) + len(self.episodes_missing)


class Show2Status:
    def __init__(self, download_directory):
        self.download_directory = download_directory

    def analyse(self, tvdb_show):
        show_status = ShowStatus(tvdb_show, self.download_directory)
        show_status.analyse()

        return show_status

    def __bool__(self):
        return True
