import asyncio
import os
import subprocess
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from pyrogram import Client
from playwright.async_api import async_playwright
from config import *
from database import connect_to_mongodb
from myjd import connect_to_jd, add_links, clear_downloads, process_and_move_links, check_for_new_links
from tools import split_video,gen_thumb, print_progress_bar


# Setup logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

db = connect_to_mongodb(MONGODB_URI, "Spidydb")
collection_name = COLLECTION_NAME

if db is not None:
    logging.info("Connected to MongoDB")

app = Client(
    name="JAVDLX-bot",
    api_hash=API_HASH,
    api_id=API_ID,
    bot_token=BOT_TOKEN,
    workers=30
)

def format_bytes(byte_count):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    index = 0
    while byte_count >= 1024 and index < len(suffixes) - 1:
        byte_count /= 1024
        index += 1
    return f"{byte_count:.2f} {suffixes[index]}"

async def create_browser_context(p, user_agent):
    """Create a browser context with the specified User-Agent."""
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(user_agent=user_agent)
    return browser, context

async def fetch_page_content(context, url):
    """Navigate to the URL and fetch the page content."""
    page = await context.new_page()
    await page.goto(url)
    await page.wait_for_load_state('networkidle')
    content = await page.content()
    await page.close()
    return content

def parse_html(html_content):
    """Parse HTML content and extract all links."""
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.find_all('a', href=True)

def filter_links(links, base_url, suffix):
    """Filter links based on the base URL and suffix."""
    return [link['href'] for link in links if link['href'].startswith(base_url) and link['href'].endswith(suffix)]

async def fetch_page():
    """Main function to fetch page and return filtered links."""
    async with async_playwright() as p:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
        url = 'https://missav.com/dm559/en/uncensored-leak'
        base_url = 'https://missav.com/'
        suffix = '-uncensored-leak'
        browser, context = await create_browser_context(p, user_agent)
        page_content = await fetch_page_content(context, url)
        links = parse_html(page_content)
        filtered_links = filter_links(links, base_url, suffix)
        await browser.close()
        return filtered_links

async def progress(current, total):
    print_progress_bar("", current, total)

def generate_thumbnail(file_name, output_filename):
    command = [
        'vcsi', file_name, '-t', '-g', '2x2',
        '--metadata-position', 'hidden',
        '--start-delay-percent', '35', '-o', output_filename
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        logging.info(f"Thumbnail saved as {output_filename}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error generating thumbnail for {file_name}: {e}")

async def process_downloads(app, device, linkgrabber):
    """Process the downloads by checking statuses and uploading to Telegram."""
    uploaded = []
    downloaded = []
    if True:
        try:
            downloads = device.downloads.query_links()
            if not downloads:
                logging.info("No active downloads.")
                await asyncio.sleep(10)
                continue
            
            for i in downloads:
                if i['bytesTotal'] == i['bytesLoaded'] and i["name"] not in downloaded:
                    file_path = os.path.join("downloads", i['name'])
                    if os.path.exists(file_path):
                        logging.info(f"{i['name']} is downloaded")
                        downloaded.append(i["name"])
                        split_files = split_video(file_path)
                        thumbnail_name = f"{i['name']}_thumb.png"
                        logging.info(file_path)
                        for file in split_files:
                            logging.info("Generating Thumbnail")
                            generate_thumbnail(file, thumbnail_name)
                            logging.info("Thumbnail generated")
                            await app.send_video(DUMP_ID, file, thumb=thumbnail_name, progress=progress)
                            os.remove(file)
                        
                        os.remove(file_path)
                        os.remove(thumbnail_name)
                        clear_downloads(device)
                else:
                    print_progress_bar(i['name'], i['bytesLoaded'], i['bytesTotal'])
                    print()
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            await asyncio.sleep(10)

async def start_download():
    async with app:
        try:
            # Connect to JD device
            jd = connect_to_jd(JD_APP_KEY, JD_EMAIL, JD_PASSWORD)
            device = jd.get_device(JD_DEVICENAME)
            logging.info('Connected to JD device')
            clear_downloads(device)
            
            # Fetch and add links
            jav_links = await fetch_page()
            logging.info(f"Total links found: {len(jav_links)}")
            responses = []
            if jav_links:
                for url in jav_links:
                    response = await add_links(device, url, "JAV")
                    responses.append(response)
                    if response:
                        logging.info(f"{url} added successfully")
                    else:
                        logging.error(f"Failed to add links: {response}")
                    linkgrabber = device.linkgrabber
                    """while True:
                        linkgrabber = device.linkgrabber
                        downloads = device.downloads.query_links()
                        if not linkgrabber.is_collecting() and downloads:
                            await asyncio.sleep(5)
                            continue"""
                    await asyncio.sleep(5)
                    new_links = await check_for_new_links(device, linkgrabber)
                    logging.info(f"Processing new links...")
                    process_and_move_links(device)
                    linkgrabber.clear_list()
                    await process_downloads(app, device, linkgrabber)  # Pass linkgrabber here
                    await asyncio.sleep(10)

        except Exception as e:
            logging.error(f"Error in start_download: {e}")

if __name__ == "__main__":
    app.run(start_download())
