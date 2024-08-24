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

def fetch_hanime_links():
    data = []
    categories = [
        "new-hanime", "tsundere", "harem", "reverse", "milf", "romance", 
        "school", "fantasy", "ahegao", "public", "ntr", "gb", "incest", 
        "uncensored", "ugly-bastard"
    ]
    base_url = 'https://hanimes.org/category/'
    
    for category in categories:
        try:
            response = requests.get(base_url + category)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article', class_='TPost B')
            
            for article in articles:
                title = article.find('h2', class_='Title').get_text().strip()
                link = article.find('div', class_='TPMvCn').find('a', href=True)['href']
                img = article.find('img', src=True)['src']
                video_links = fetch_video_links(link)
                
                if video_links:
                    data.append([title, img, video_links[0]])
                if len(data) == 10:
                    return data
        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve content for category {category}: {e}")
    return data

def fetch_video_links(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return [source['src'] for source in soup.find_all('source', src=True)]
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve video content from {url}: {e}")
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
                documents = find_documents(db, collection_name)
                downloaded_files = [doc["File_Name"] for doc in documents]
                hanime_links = random.sample(fetch_hanime_links(), min(100, len(fetch_hanime_links())))
                print(f"Total links found: {len(hanime_links)}")

                for title, thumb, url in hanime_links:
                    file_path = f"Downloads/{title}.mp4"
                    thumb_path = f"Downloads/{title}.png"
                    if file_path not in downloaded_files:
                        print(f"Starting download: {title} from {url}")
                        download = add_download(api, url, file_path)
                        while not download.is_complete:
                            download.update()
                            print(f"Current Progress: {download.progress:.2f}%")

                        print(f"{file_path} Download Completed")
                        generate_thumbnail(file_path, thumb_path)
                        
                        if download.is_complete:
                            video_message = await app.send_video(
                                DUMP_ID, video=file_path, thumb=thumb_path, caption=title
                            )
                            result = {
                                "ID": video_message.id,
                                "File_Name": file_path,
                                "Video_Link": url,
                            }
                            insert_document(db, collection_name, result)
                            os.remove(file_path)
                            os.remove(thumb_path)
            except Exception as e:
                print(f"Error during download process: {e}")

if __name__ == "__main__":
    app.run(start_download())
