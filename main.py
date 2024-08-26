import asyncio
import os
import subprocess
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from pyrogram import Client
from config import *
from downloader import *
from database import connect_to_mongodb, find_documents, insert_document
import static_ffmpeg



static_ffmpeg.add_paths()
# Connect to aria2
api = connect_aria2()

# Database connection
db = connect_to_mongodb(MONGODB_URI, "Spidydb")
collection_name = "Hanime"

# Pyrogram client initialization
app = Client(
    name="HanimeDLX-bot",
    api_hash=API_HASH,
    api_id=int(API_ID),
    bot_token=BOT_TOKEN,
    workers=300
)

def format_bytes(byte_count):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    index = 0
    while byte_count >= 1024 and index < len(suffixes) - 1:
        byte_count /= 1024
        index += 1
    return f"{byte_count:.2f} {suffixes[index]}"

import requests
from bs4 import BeautifulSoup
import time

def fetch_hanime_data():
    documents = find_documents(db, collection_name)
    downloaded_files = {doc["File_Name"] for doc in documents}
    links = []
    page = 1
    base_url = 'https://hanimes.org/category/'
    categories = [
        "category/new-hanime", "category/tsundere", "category/harem", "category/reverse", "category/milf", "category/romance", 
        "category/school", "category/fantasy", "category/ahegao", "category/public", "category/ntr", "category/gb", "category/incest", 
        "tag/uncensored", "category/ugly-bastard"
    ]

    with requests.Session() as session:
        while len(links) < 100:
            pagel = f"/page/{page}/"
            for category in categories:
                try:
                    response = session.get(f"{base_url}{category}{pagel}")
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    articles = soup.find_all('article', class_='TPost B')

                    for article in articles:
                        title = article.find('h2', class_='Title').get_text(strip=True)
                        link = article.find('div', class_='TPMvCn').find('a', href=True)['href']
                        img = article.find('img', src=True)['src']
                        file_name = f"{title}.mp4"

                        if file_name not in downloaded_files:
                            # Fetch video links
                            video_links = fetch_video_links(session, link)
                            if video_links:
                                links.append([title, img, video_links[0]])
                                if len(links) >= 100:
                                    break  # Exit if we have enough links
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching category {category} on page {page}: {e}")
                    time.sleep(2)  # Wait before retrying

            page += 1

    return links

def fetch_video_links(session, link):
    """Fetch video links from the provided link."""
    try:
        video_response = session.get(link)
        video_response.raise_for_status()
        return [source['src'] for source in BeautifulSoup(video_response.text, 'html.parser').find_all('source', src=True)]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching video content from {link}: {e}")
        return []



async def progress(current, total):
    print(f"Download Progress: {current * 100 / total:.1f}%")
         
def generate_thumbnail(file_name, output_filename):
    command = [
        'vcsi', file_name, '-t', '-g', '2x2',
        '--metadata-position', 'hidden',
        '--start-delay-percent', '35', '-o', output_filename
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        print(f"Thumbnail saved as {output_filename}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating thumbnail for {file_name}: {e}")

async def start_download():
    async with app:
        while True:
            try:
                hanime_links = fetch_hanime_links()
                print(f"Total links found: {len(hanime_links)}")
                for title, thumb, url in hanime_links:
                    file_path = f"Downloads/{title}.mp4"
                    file_name = f"{title}.mp4"
                    thumb_path = f"Downloads/{title}.png"
                    print(f"Starting download: {title} from {url}")
                    download = add_download(api, url, file_path)
                    while not download.is_complete:
                            download.update()
                    print(f"{file_path} Download Completed")
                    generate_thumbnail(file_path, thumb_path)    
                    if download.is_complete:
                            video_message = await app.send_video(
                                DUMP_ID, video=file_path, thumb=thumb_path, caption=title
                            )
                            result = {
                                "ID": video_message.id,
                                "File_Name": file_name,
                                "Video_Link": url,
                            }
                            insert_document(db, collection_name, result)
                            os.remove(file_path)
                            os.remove(thumb_path)
            except Exception as e:
                print(f"Error during download process: {e}")
        asnycio.sleep(1200)

if __name__ == "__main__":
    app.run(start_download())
