class Status:
    def __init__(self, episodes_behind, episodes_missing):
        self.episodes_behind = episodes_behind
        self.episodes_missing = episodes_missing

    def __str__(self):
        behind_ = 'is {} episodes behind'.format(len(self.episodes_behind)) if self.episodes_behind else 'is up-to-date'
        missing_ = 'has {} missing episodes'.format(len(self.episodes_missing)) if self.episodes_missing else ''

        return ' and '.join([i for i in (behind_, missing_) if i])

    def __len__(self):
        return len(self.episodes_behind) + len(self.episodes_missing)
