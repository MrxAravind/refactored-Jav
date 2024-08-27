import aria2p

# Connect to aria2c daemon
def connect_aria2():
    return aria2p.API(
        aria2p.Client(
            host="http://localhost",  # Change this if your aria2c daemon is hosted elsewhere
            port=6800,
            secret=""  # If you have an RPC secret, add it here
        )
    )

# Add a download with a specified filename
def add_download(api, url, filename):
    try:
        # Set the options for the download
        options = {"out": filename}  # Specify the desired filename
        download_list = api.add(url, options=options)

        # Collect the gids
        gids = []

        if isinstance(download_list, list):
            for download in download_list:
                print(f"Download added: {download.gid} with filename: {filename}")
                gids.append(download)
        else:
            download = download_list
            print(f"Download added: {download.gid} with filename: {filename}")
            gids.append(download)

        return gids[0]
    except Exception as e:
        print(f"Failed to add download: {e}")
        return None


# Pause a download by GID
def pause_download(api, gid):
    try:
        api.pause(gid)
        print(f"Download paused: {gid}")
    except Exception as e:
        print(f"Failed to pause download: {e}")

# Resume a download by GID
def resume_download(api, gid):
    try:
        api.resume(gid)
        print(f"Download resumed: {gid}")
    except Exception as e:
        print(f"Failed to resume download: {e}")

# Remove a download by GID
def remove_download(api, gid):
    try:
        api.remove([gid], force=True)
        print(f"Download removed: {gid}")
    except Exception as e:
        print(f"Failed to remove download: {e}")

# Get the status of all downloads
def get_downloads_status(api):
    try:
        downloads = api.get_downloads()
        for download in downloads:
            print(f"GID: {download.gid}, Status: {download.status}, Progress: {download.progress_string()}")
    except Exception as e:
        print(f"Failed to retrieve downloads status: {e}")

# Purge completed/removed downloads
def purge_downloads(api):
    try:
        api.purge()
        print("Purged completed/removed downloads")
    except Exception as e:
        print(f"Failed to purge downloads: {e}")
