import os

import requests
from dotenv import load_dotenv

load_dotenv()
TG_API = os.getenv("BOT_API_KEY")
web_hook = '6caf-194-54-176-118.ngrok.io'

r = requests.get(f"https://api.telegram.org/bot{TG_API}/setWebhook?url=https://{web_hook}/")

print(r.json())