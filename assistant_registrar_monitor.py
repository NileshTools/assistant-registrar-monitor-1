import requests
from bs4 import BeautifulSoup
import json
import os
import telegram
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Telegram credentials from GitHub Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Load target websites
with open("targets.json", "r") as f:
    TARGETS = json.load(f)

# Track notified items
SEEN_FILE = "seen_notices.json"
FIRST_RUN = False  # Change to True for first run initialization

if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_notices = set(json.load(f))
else:
    seen_notices = set()
    FIRST_RUN = True  # No previous data, first run

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
        site_notices = []

        # === IIT ISM Dhanbad ===
        if "iitism.ac.in" in url:
            table = soup.find("table")
            if table:
                for row in table.find_all("tr"):
                    cols = row.find_all("td")
                    if cols:
                        notice_text = cols[0].get_text(strip=True)
                        a_tag = cols[0].find("a", href=True)
                        if a_tag:
                            href = a_tag["href"]
                            if not href.startswith("http"):
                                href = requests.compat.urljoin(url, href)
                        else:
                            href = url  # fallback
                        site_notices.append((notice_text, href))

        # === Other sites: Assistant Registrar ===
        else:
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if text and "assistant registrar" in text.lower():
                    href = a["href"]
                    if not href.startswith("http"):
                        href = requests.compat.urljoin(url, href)
                    site_notices.append((text, href))

        # === Process notices ===
        for notice_text, href in site_notices:
            notice_id = f"{name} | {notice_text}"  # unique identifier per org+notice
            if notice_id not in seen_notices:
                if not FIRST_RUN:
                    send_message(f"📢 New notice at {name}:\n{notice_text}\n🔗 {href}")
                seen_notices.add(notice_id)
                updated = True

    if updated:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_notices), f)

if __name__ == "__main__":
    if FIRST_RUN:
        print("⚡ First run detected: initializing seen notices without sending notifications...")
    else:
        print("🔍 Checking sites for new notices...")

    check_sites()
    print("✅ Done.")
