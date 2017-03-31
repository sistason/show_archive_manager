import logging
import re

from a_argument_to_show.thetvdb_api import TheTVDBAPI


class Argument2Show:

    def __init__(self):
        self.tvdb_api = TheTVDBAPI()
        self.re_year = re.compile(r'({})'.format('|'.join(map(str, range(1900, 2040)))))

    def argument2show(self, argument_show):
        logging.debug('Converting argument "{}" to show...'.format(argument_show))
        imdb_id = re.search(r'(?P<id>tt\d{7})', argument_show)
        if imdb_id:
            show = self.tvdb_api.get_show_by_imdb_id(imdb_id.group('id'))
            logging.info('Found show "{}" for argument "{}"'.format(show, argument_show))
            return show

        year = self.re_year.search(argument_show)
        if year:
            argument_show = (argument_show[:year.start()] + argument_show[year.end():]).strip().replace('  ', ' ')
            year = year.group(1)

        return self._search_for_title(argument_show, year=year)

    def _search_for_title(self, title, year=None):
        shows = self.tvdb_api.get_shows_by_search(title, year=year)
        if shows:
            if len(shows) == 1:
                return shows[0]

            logging.info('Found {} matches for argument "{}"'.format(len(shows), title))
            best_result = max([s for s in shows if s and s.raw.get('overview')], key=len)
            logging.info('Best result for Argument "{}" is "{}"'.format(title, repr(best_result)))

            if logging.getLogger(__name__).level <= logging.INFO:
                return self._interactive_select_show(title, shows, best_result)

            return best_result

    def __bool__(self):
        return bool(self.tvdb_api)

    @staticmethod
    def _interactive_select_show(title, shows, best_result):
        shows.sort(key=lambda s: s.aired)
        logging.info('Select which show best matches argument "{}":'.format(title))
        for i, s_ in enumerate(shows):
            logging.info('{}{:2}: {}'.format('!' if s_ == best_result else ' ', i, s_.get_brief()))

        selection = input('Input a <number> or blank for the best result (indicator: "!")')
        if not selection:
            return best_result
        if not selection.isdigit():
            return None
        return shows[int(selection)]

