class Status:
    def __init__(self, seasons_missing, episodes_missing):
        self.episodes_missing = episodes_missing
        self.seasons_missing = seasons_missing

    def __str__(self):
        season_, episode_ = '', ''
        if self.seasons_missing:
            season_ = 'has seasons missing: {}'.format(self.seasons_missing)
        if self.episodes_missing:
            episode_ = 'has episodes missing: {}'.format(self.episodes_missing)

        return ' and '.join([i for i in (season_, episode_) if i])

    def __len__(self):
        return len(self.episodes_missing) + sum([len(s.episodes) for s in self.seasons_missing])
