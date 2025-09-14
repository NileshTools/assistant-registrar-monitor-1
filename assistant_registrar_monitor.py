import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import telegram

# Load Telegram credentials from GitHub Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Load target websites
with open("targets.json", "r") as f:
    TARGETS = json.load(f)

# Keep track of already seen links (to avoid duplicate notifications)
SEEN_FILE = "seen_links.json"
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_links = set(json.load(f))
else:
    seen_links = set()

def send_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=True)
    except Exception as e:
        print("Error sending message:", e)

def check_sites():
    global seen_links
    updated = False
    for site in TARGETS:
        name = site["name"]
        url = site["url"]

        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"❌ Failed to fetch {name}: {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        # Collect all links on the page
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]

            # Absolute URL
            if not href.startswith("http"):
                href = requests.compat.urljoin(url, href)

            links.append((text, href))

        for text, href in links:
            # If new link not seen before
            if href not in seen_links:
                # Always notify for IIT ISM Dhanbad notices page
                if "ism" in url or "iitism" in url:
                    send_message(f"📢 New notice at {name}:\n{text}\n{href}")
                    seen_links.add(href)
                    updated = True

                # Notify if "Assistant Registrar" appears (case-insensitive)
                if re.search(r"assistant\s*registrar", text, re.IGNORECASE):
                    send_message(f"🎯 Assistant Registrar update at {name}:\n{text}\n{href}")
                    seen_links.add(href)
                    updated = True

    # Save updated seen links
    if updated:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_links), f)

if __name__ == "__main__":
    print("🔍 Checking sites...")
    check_sites()
    print("✅ Done.")
