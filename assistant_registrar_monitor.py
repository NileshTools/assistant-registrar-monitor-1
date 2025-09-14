import requests
from bs4 import BeautifulSoup
import json
import os
import re
import telegram
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

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
            r = requests.get(url, timeout=20, headers=HEADERS, verify=False)
            r.raise_for_status()
        except Exception as e:
            print(f"❌ Failed to fetch {name}: {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        # Special handling for IIT ISM Dhanbad - restrict to actual notices
        if "iitism.ac.in" in url:
            notices_div = soup.find("div", class_="table-responsive")  # This class contains actual notices
            if notices_div:
                links = []
                for a in notices_div.find_all("a", href=True):
                    text = a.get_text(strip=True)
                    href = a["href"]
                    if not href.startswith("http"):
                        href = requests.compat.urljoin(url, href)
                    links.append((text, href))
            else:
                links = []
        else:
            # Generic scraping for other sites
            links = []
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                href = a["href"]
                if not href.startswith("http"):
                    href = requests.compat.urljoin(url, href)
                links.append((text, href))

        # Check and send notifications
        for text, href in links:
            if href not in seen_links:
                # Always notify for IIT ISM Dhanbad
                if "iitism.ac.in" in url:
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
