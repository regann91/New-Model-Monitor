import os
import json
import requests
from bs4 import BeautifulSoup

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")  # the address you signed up to Resend with
CACHE_FILE = "last_seen_posts.json"

TARGET_URLS = {
    "kie": "https://kie.ai/changelog",
    "fal": "https://fal.ai/explore/recently-added"
}

def send_email(subject, html_body):
    if not RESEND_API_KEY or not NOTIFY_EMAIL:
        print("Error: RESEND_API_KEY or NOTIFY_EMAIL is missing.")
        return
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": "Changelog Monitor <onboarding@resend.dev>",
                "to": [NOTIFY_EMAIL],
                "subject": subject,
                "html": html_body,
            },
            timeout=15,
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending email: {e}")

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

        entries = soup.find_all(["h1", "h2", "h3"])
        current_kie_posts = [el.get_text(strip=True) for el in entries if el.get_text(strip=True)]
        new_cache["kie"] = current_kie_posts

        if cache["kie"]:
            new_posts = [p for p in current_kie_posts if p not in cache["kie"]]
            for post in new_posts:
                send_email(
                    "🔔 New Kie.ai Changelog Post",
                    f"<p>{post}</p><p><a href='{TARGET_URLS['kie']}'>View Changelog</a></p>",
                )
    except Exception as e:
        print(f"Failed to check Kie.ai: {e}")
        new_cache["kie"] = cache["kie"]

    # --- 2. Check Fal.ai Recently Added ---
    try:
        res = requests.get(TARGET_URLS["fal"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        model_elements = soup.find_all(["h1", "h2", "h3", "p", "div"])
        current_fal_models = list({
            el.get_text(strip=True)
            for el in model_elements
            if el.get_text(strip=True) and len(el.get_text(strip=True)) < 80
        })
        new_cache["fal"] = current_fal_models

        if cache["fal"]:
            new_models = [m for m in current_fal_models if m not in cache["fal"]]
            for model in new_models:
                send_email(
                    "🚀 New Model Added on Fal.ai",
                    f"<p>{model}</p><p><a href='{TARGET_URLS['fal']}'>Explore Models</a></p>",
                )
    except Exception as e:
        print(f"Failed to check Fal.ai: {e}")
        new_cache["fal"] = cache["fal"]

    save_cache(new_cache)

if __name__ == "__main__":
    check_updates()
