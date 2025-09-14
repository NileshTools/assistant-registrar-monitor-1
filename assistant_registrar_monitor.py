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

        # === Find the first notice ===
        first_notice = None

        # Special handling for IIT ISM Dhanbad
        if "iitism.ac.in" in url:
            table = soup.find("table")
            if table:
                row = table.find("tr")
                if row:
                    cols = row.find_all("td")
                    if cols:
                        notice_text = cols[0].get_text(strip=True)
                        a_tag = cols[0].find("a", href=True)
                        if a_tag:
                            href = a_tag["href"]
                            if not href.startswith("http"):
                                href = requests.compat.urljoin(url, href)
                        else:
                            href = url
                        first_notice = (notice_text, href)
        else:
            # Generic: first link containing notice/recruitment
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if text and ("recruitment" in text.lower() or "notice" in text.lower() or "assistant registrar" in text.lower()):
                    href = a["href"]
                    if not href.startswith("http"):
                        href = requests.compat.urljoin(url, href)
                    first_notice = (text, href)
                    break  # only first notice

        # Send notification
        if first_notice:
            notice_text, href = first_notice
            send_message(f"📢 Latest notice at {name}:\n{notice_text}\n🔗 {href}")
            print(f"Sent notification for {name}")

if __name__ == "__main__":
    print("🔍 Checking top notices for each organization...")
    check_sites()
    print("✅ Done.")
