import asyncio
import logging
import os
import subprocess
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pyrogram import Client
from swibots import BotApp
from telegraph import Telegraph, exceptions

from config import API_HASH, API_ID, BOT_TOKEN, COMMUNITY_ID, DUMP_ID, INDEX_ID, LOG_ID, MONGODB_URI, TOKEN
from database import connect_to_mongodb, find_documents, insert_document
from techzdl import TechZDL
import static_ffmpeg

# Initialize logging
logging.basicConfig(
    filename='hanimedlx.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ffmpeg installed on first call to add_paths()
static_ffmpeg.add_paths()

# Database connection
mongodb_uri = MONGODB_URI
database_name = "Spidydb"
collection_name = "Hanime"
db = connect_to_mongodb(mongodb_uri, database_name)

# Pyrogram and Swibots client initialization
app = Client(
    name="HanimeDLX-bot",
    api_hash=API_HASH,
    api_id=int(API_ID),
    bot_token=BOT_TOKEN,
    workers=300
)
bot = BotApp(TOKEN)


def format_bytes(byte_count):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    index = 0
    while byte_count >= 1024 and index < len(suffixes) - 1:
        byte_count /= 1024
        index += 1
    return f"{byte_count:.2f} {suffixes[index]}"


async def progress_callback(current, total, title, status, start_time):
    elapsed_time = time.time() - start_time
    if round(elapsed_time % 10.00) == 0 or current == total:
        percentage = f"{current * 100 / total:.1f}%"
        text = (f"{status.text}\nHanime: {title}\nStatus: Uploading\n"
                f"Progress: {format_bytes(current)} / {format_bytes(total)} [{percentage}]\n"
                f"Time: {datetime.now()}")
        if status.text != text:
            await status.edit_text(text)


async def switch_upload(file_path, thumb, progress_args):
    response = await bot.send_media(
        message=os.path.basename(file_path),
        community_id=COMMUNITY_ID,
        group_id=GROUP_ID,
        document=file_path,
        thumb=thumb,
        part_size=50 * 1024 * 1024,
        task_count=10,
        progress=progress_callback,
        progress_args=progress_args
    )
    return response


def generate_thumbnail(file_name, output_filename):
    command = [
        'vcsi', file_name, '-t', '-g', '2x2',
        '--metadata-position', 'hidden',
        '--start-delay-percent', '25', '-o', output_filename
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        logger.info(f"Thumbnail saved as {output_filename}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating thumbnail: {e}")


def fetch_hanime_links():
    data = []
    categories = [
        "new-hanime", "tsundere", "harem", "reverse", "milf", "romance", 
        "school", "fantasy", "ahegao", "public", "ntr", "gb", "incest", 
        "uncensored", "ugly-bastard"
    ]
    base_url = 'https://hanimes.org/category/'
    
    for category in categories:
        response = requests.get(base_url + category)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article', class_='TPost B')
            
            for article in articles:
                title = article.find('h2', class_='Title').get_text().strip()
                link = article.find('div', class_='TPMvCn').find('a', href=True)['href']
                img = article.find('img', src=True)['src']
                video_links = fetch_video_links(link)
                
                if video_links:
                    data.append([title, img, video_links[0]])
        else:
            logger.error(f"Failed to retrieve content. Status code: {response.status_code}")
    
    return data


def fetch_video_links(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        return [source['src'] for source in soup.find_all('source', src=True)]
    else:
        logger.error(f"Failed to retrieve video content. Status code: {response.status_code}")
        return []


def upload_image_to_telegraph(image_path):
    try:
        telegraph = Telegraph()
        telegraph.create_account(short_name='PythonTelegraphBot')
        response = telegraph.upload_file(image_path)
        if isinstance(response, list) and response:
            return f"http://graph.org{response[0]['src']}"
    except exceptions.TelegraphException as e:
        logger.error(f"TelegraphException occurred: {e}")
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
    return None


async def start_download():
    async with app:
        while True:
            documents = find_documents(db, collection_name)
            downloaded_files = [doc["File_Name"] for doc in documents]
            hanime_links = fetch_hanime_links()
            logger.info(f"Total links found: {len(hanime_links)}")
            
            status = await app.send_message(LOG_ID, f"Bot Started\nTotal Links: {len(hanime_links)}")
            uploaded_count = 0
            
            try:
                for title, thumb, url in hanime_links:
                    file_path = f"{title}.mp4"
                    if file_path not in downloaded_files:
                        await status.edit_text(f"{status.text}\nHanime: {title}\nStatus: Downloading\nTime: {datetime.now()}")
                        start_time = time.time()
                        
                        downloader = TechZDL(
                            url=url,
                            debug=False,
                            filename=file_path,
                            progress=True,
                            progress_callback=progress_callback,
                            progress_args=(title, status, start_time)
                        )
                        await downloader.start()
                        file_info = await downloader.get_file_info()
                        
                        if downloader.download_success:
                            generate_thumbnail(f"downloads/{file_path}", "thumb.png")
                            thumb_url = upload_image_to_telegraph("thumb.png")
                            
                            upload_response = await switch_upload(file_path, "thumb.png", (title, status, start_time, file_info['total_size']))
                            video_message = await app.send_video(DUMP_ID, video=f"downloads/{file_path}", thumb="thumb.png", caption=file_path, progress=progress_callback, progress_args=(title, status, start_time))
                            
                            await app.send_photo(
                                INDEX_ID,
                                photo=thumb,
                                caption=f"Tg File: [File](https://t.me/c/{str(video_message.chat.id).replace('-100','')}/{video_message.id})\nDirect Link: [Direct Link]({upload_response.media_link})"
                            )
                            
                            uploaded_count += 1
                            result = {
                                "ID": video_message.id,
                                "Thumbnail": thumb_url,
                                "File_Name": file_path,
                                "Video_Link": url,
                                "Media_Link": upload_response.media_link
                            }
                            insert_document(db, collection_name, result)
                            os.remove(f"downloads/{file_path}")
                            os.remove("thumb.png")
            except Exception as e:
                logger.error("Failed to download video", exc_info=e)
                await status.edit_text(f"{status.text}\nHanime: {file_path}\nDownloaded Videos: {uploaded_count}\nStatus: Error")
            if len(hanime_links) == uploaded_count:
                await status.edit_text(f"{status.text}\nHanime: {file_path}\nDownloaded Videos: {uploaded_count}\nStatus: Finished")
            await asyncio.sleep(120)


if __name__ == "__main__":
    app.run(start_download())
