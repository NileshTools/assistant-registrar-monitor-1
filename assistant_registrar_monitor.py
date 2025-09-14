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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

# File to track already notified notices
SEEN_FILE = "seen_notices.json"
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen_notices = json.load(f)
else:
    seen_notices = {}

def send_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=True)
    except Exception as e:
        print("Error sending message:", e)

def check_sites():
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

        # === Find all notices related to Assistant Registrar ===
        new_notices = []

        # IIT ISM Dhanbad specific handling
        if "iitism.ac.in" in url:
            table = soup.find("table")
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if cols:
                        text = cols[0].get_text(strip=True)
                        if "assistant registrar" in text.lower():
                            a_tag = cols[0].find("a", href=True)
                            link = a_tag["href"] if a_tag else url
                            if not link.startswith("http"):
                                link = requests.compat.urljoin(url, link)
                            new_notices.append((text, link))
        else:
            # Generic handling: links containing "assistant registrar"
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if "assistant registrar" in text.lower():
                    link = a["href"]
                    if not link.startswith("http"):
                        link = requests.compat.urljoin(url, link)
                    new_notices.append((text, link))

        # Check for already seen notices
        seen = seen_notices.get(name, [])
        for text, link in new_notices:
            if text not in seen:
                send_message(f"📢 New Assistant Registrar notice at {name}:\n{text}\n🔗 {link}")
                seen.append(text)

        # Update seen notices
        seen_notices[name] = seen

    # Save seen notices
    with open(SEEN_FILE, "w") as f:
        json.dump(seen_notices, f, indent=2)

if __name__ == "__main__":
    print("🔍 Checking Assistant Registrar notices...")
    check_sites()
    print("✅ Done.")
