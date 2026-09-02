import os
import json
import requests
from bs4 import BeautifulSoup

# Reads securely from GitHub Actions secret
WECOM_WEBHOOK_URL = os.environ.get("WECOM_WEBHOOK_URL")
CACHE_FILE = "last_seen_posts.json"

TARGET_URLS = {
    "kie": "https://kie.ai/changelog",
    "fal": "https://fal.ai/explore/recently-added"
}

def send_to_wecom(markdown_text):
    if not WECOM_WEBHOOK_URL:
        print("Error: WECOM_WEBHOOK_URL environment variable is missing.")
        return
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": markdown_text
        }
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(WECOM_WEBHOOK_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending to WeCom: {e}")

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {"kie": [], "fal": []}

def save_cache(cache_data):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=4)

def check_updates():
    cache = load_cache()
    new_cache = {"kie": [], "fal": []}

    # --- 1. Check Kie.ai Changelog ---
    try:
        res = requests.get(TARGET_URLS["kie"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
