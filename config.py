from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.environ.get('TELEGRAM_API', '')
API_HASH = os.environ.get('TELEGRAM_HASH', '')
DUMP_ID = int(os.environ.get('DUMP_CHAT_ID', ''))
MONGODB_URI = os.getenv("MONGODB_URI")
