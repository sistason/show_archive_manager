

class ShowStatus:
    def __init__(self, show, dir):
        self.show = show
        self.download_directory = dir
        self.current_episode = (0,0)
        self.episode_holes = []

class Show2Status:
    def __init__(self, download_directory):
        self.download_directory = download_directory

    def analyse(self, imdb_show):
        show_status = ShowStatus(imdb_show, self.download_directory)

        return show_status