# Show Downloader

Uses Piratebay and Premiumize.me to update/fill holes in your tv-show storage.

## Usage

python manager.py $show_names $storage_directory
 - $show_names: Names or imdb-ids of the show. Skip to use all directories in $storage_directory as names
 - $storage_directory
 - -a password/password_file: "username:password", or a file containing this syntax.
 - -u/--update_missing: Only keep the latest season up-to-date or try to fix holes in the whole show?
 - -q/--quality: Set the quality to filter results of episodes
 - -e/--encoder: Set the encoder to filter results of episodes

## Workflow

* translate argument $show_name to show
* Get the state of the show on disk (seasons/episodes existing, holes and latest episodes)
* Search Piratebay for links of the missing episodes
  * Filter the links for quality/encoder
* Make premiumize.me download the torrent
  * Wait for premiumize.me to finish the torrent
* Download the file from premiumize.me

## Dependencies
- python >=3.5.2
- bs4 + lxml
- aiohttp
- aiofiles