## Show Downloader

1. translate argument_show to show_name
2. Looks at filesystem structure, see if show exists
    - if yes:
        get state (missing + current)
    - if no:
        empty, get everything
3. List of shows to get, throw to $site (piratebay)
    parse outputs and get most fitting for quality
4. Download file via premiumize.me
5. On premiumize.me-DL-finish:
    download to fitting location and delete
