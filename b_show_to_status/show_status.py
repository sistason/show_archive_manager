class Status:
    def __init__(self, seasons_missing, episodes_missing):
        self.episodes_missing = episodes_missing
        self.seasons_missing = seasons_missing

    def __str__(self):
        season_, episode_ = '', ''
        if self.seasons_missing:
            season_ = 'has {} missing season'.format(len(self.seasons_missing))
            season_ += 's' if len(self.seasons_missing) > 1 else ''
        if self.episodes_missing:
            episode_ = 'has {} missing episode'.format(len(self.episodes_missing))
            episode_ += 's' if len(self.episodes_missing) > 1 else ''

        return ' and '.join([i for i in (season_, episode_) if i])

    def __len__(self):
        return len(self.episodes_missing) + sum([len(s.episodes) for s in self.seasons_missing])
