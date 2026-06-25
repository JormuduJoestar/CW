import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

DB_NAME = "bot_database.db"

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME")

PROXY = {
    "scheme": "socks5",
    "hostname": "127.0.0.1",
    "port": 1080,
    # "username": "логин",
    # "password": "пароль"
}
