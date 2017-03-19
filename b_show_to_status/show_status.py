class ShowStatus:
    def __init__(self, show, download_directory):
        self.show = show
        self.download_directory = download_directory
        self.episodes_behind = None
        self.episodes_missing = None
        self.download_links = None

    def __str__(self):
        behind_ = 'is {} episodes behind'.format(len(self.episodes_behind)) if self.episodes_behind else ''
        missing_ = 'has {} missing episodes'.format(len(self.episodes_missing)) if self.episodes_missing else ''

        return 'Show "{}" {}'.format(self.show.name, 'and '.join([i for i in (behind_, missing_) if i]))

    def __len__(self):
        return len(self.episodes_behind) + len(self.episodes_missing)
