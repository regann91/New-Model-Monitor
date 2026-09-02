import os
import json
import requests
from bs4 import BeautifulSoup

# Reads securely from GitHub Action environment variables
WECOM_WEBHOOK_URL = os.environ.get("WECOM_WEBHOOK_URL")
CACHE_FILE = "last_seen_posts.json"

TARGET_URLS = {
    "kie": "https://kie.ai",
    "fal": "https://fal.ai"
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
        response = requests.post(WECOM_WEBHOOK_URL, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending to WeCom: {e}")

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {"kie":, "fal":}

def save_cache(cache_data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=4)

def check_updates():
    cache = load_cache()
    new_cache = {"kie":, "fal":}
    
    # --- 1. Check Kie.ai Changelog ---
    try:
        res = requests.get(TARGET_URLS["kie"], timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Generic title capture (adjust according to live site's DOM tags if needed)
        entries = soup.find_all(['h', 'h', 'h'])
        current_kie_posts = [elget_text(strip=True) for el in entries if elget_text(strip=True)]
        new_cache["kie"] = current_kie_posts
        
        if cache["kie"]:
            new_posts = [p for p in current_kie_posts if p not in cache["kie"]]
            for post in new_posts:
                msg = f"🔔 **New Kie.ai Changelog Post**\n\n> {post}\n\n[View Changelog]({TARGET_URLS['kie']})"
                send_to_wecom(msg)
    except Exception as e:
        print(f"Failed to check Kie.ai: {e}")
        new_cache["kie"] = cache["kie"]

    # --- 2. Check Fal.ai Recently Added ---
    try:
        res = requests.get(TARGET_URLS["fal"], timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Generic element capture
        model_elements = soup.find_all(['h', 'h', 'p', 'div'])
        current_fal_models = list(set([elget_text(strip=True) for el in model_elements if len(elget_text(strip=True)) < ]))
        new_cache["fal"] = current_fal_models
        
        if cache["fal"]:
            new_models = [m for m in current_fal_models if m not in cache["fal"]]
            for model in new_models:
                msg = f"🚀 **New Model Added on Fal.ai**\n\n> {model}\n\n[Explore Models]({TARGET_URLS['fal']})"
                send_to_wecom(msg)
    except Exception as e:
        print(f"Failed to check Fal.ai: {e}")
        new_cache["fal"] = cache["fal"]

    save_cache(new_cache)

if __name__ == "__main__":
    check_updates()
