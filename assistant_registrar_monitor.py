import requests
from bs4 import BeautifulSoup
import json
import os
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

# Track notified items to avoid duplicates
SEEN_FILE = "seen_notices.json"
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_notices = set(json.load(f))
else:
    seen_notices = set()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

def send_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print("Error sending message:", e)

def check_sites():
    global seen_notices
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

        # Generate unique notice identifiers per site
        site_notices = set()

        # Special handling for IIT ISM Dhanbad: only first table
        if "iitism.ac.in" in url:
            table = soup.find("table")
            if table:
                for row in table.find_all("tr"):
                    cols = row.find_all("td")
                    if cols:
                        notice_text = cols[0].get_text(strip=True)
                        if notice_text:
                            site_notices.add(notice_text)
        else:
            # Generic scraping: all <a> text
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if text:
                    site_notices.add(text)

        # Check for new notices
        for notice_text in site_notices:
            if notice_text not in seen_notices:
                # Always notify for IIT ISM Dhanbad / general notices
                if "iitism.ac.in" in url:
                    send_message(f"📢 New notice/advertisement published at {name}")
                    seen_notices.add(notice_text)
                    updated = True
                # Assistant Registrar detection
                elif "assistant registrar" in notice_text.lower():
                    send_message(f"🎯 New Assistant Registrar update at {name}")
                    seen_notices.add(notice_text)
                    updated = True

    # Save updated seen notices
    if updated:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_notices), f)

if __name__ == "__main__":
    print("🔍 Checking sites...")
    check_sites()
    print("✅ Done.")
