import os

import requests
from dotenv import load_dotenv

load_dotenv()
TG_API = os.getenv("BOT_API_KEY")
web_hook = '038b-194-54-176-103.ngrok.io'

r = requests.get(f"https://api.telegram.org/bot{TG_API}/setWebhook?url=https://{web_hook}/")

print(r.json())