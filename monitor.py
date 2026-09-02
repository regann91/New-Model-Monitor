import os
import re
import json
import requests
from playwright.sync_api import sync_playwright

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")  # the address you signed up to Resend with
CACHE_FILE = "last_seen_posts.json"

FAL_URL = "https://fal.ai/explore/recently-added"
KIE_URL = "https://kie.ai/changelog"

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
    return {"kie": [], "fal": {}}

def save_cache(cache_data):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=4)

def check_fal(cache, new_cache):
    # fal.ai embeds the model list as escaped JSON directly in the server-rendered
    # HTML, so a plain HTTP GET is enough here — no browser needed.
    try:
        res = requests.get(FAL_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        html = res.text
        pattern = re.compile(r'\\"endpoint\\":\\"([^\\]+)\\",\\"title\\":\\"([^\\]+)\\"')
        current = {endpoint: title for endpoint, title in pattern.findall(html)}
        new_cache["fal"] = current

        if cache.get("fal"):
            new_entries = {k: v for k, v in current.items() if k not in cache["fal"]}
            for endpoint, title in new_entries.items():
                send_email(
                    f"🚀 New Model on Fal.ai: {title}",
                    f"<p><b>{title}</b></p><p>{endpoint}</p>"
                    f"<p><a href='https://fal.ai/models/{endpoint}'>View Model</a></p>",
                )
    except Exception as e:
        print(f"Failed to check Fal.ai: {e}")
        new_cache["fal"] = cache.get("fal", {})

def check_kie(cache, new_cache):
    # kie.ai's changelog is rendered client-side, and its Cloudflare Worker serves an
    # empty "No updates found" stub to plain HTTP clients — a real browser is required.
    # Note: don't wait for "networkidle" here — kie.ai has ongoing background requests
    # (analytics/chat widget) that never let the network go fully idle, so that wait
    # condition times out even though the real content loads within a few seconds.
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                viewport={"width": 1280, "height": 900},
            )
            page.goto(KIE_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_selector("div.group.rounded-2xl.border", timeout=25000)
            cards = page.query_selector_all("div.group.rounded-2xl.border")

            current = []
            for card in cards:
                title_el = card.query_selector("h3")
                date_el = card.query_selector("span.text-sm.font-medium")
                if title_el:
                    title = title_el.inner_text().strip()
                    date = date_el.inner_text().strip() if date_el else ""
                    current.append(f"{date} | {title}")
            browser.close()

        new_cache["kie"] = current

        if cache.get("kie"):
            new_posts = [p for p in current if p not in cache["kie"]]
            for post in new_posts:
                send_email(
                    "🔔 New Kie.ai Changelog Post",
                    f"<p>{post}</p><p><a href='{KIE_URL}'>View Changelog</a></p>",
                )
    except Exception as e:
        print(f"Failed to check Kie.ai: {e}")
        new_cache["kie"] = cache.get("kie", [])

def check_updates():
    cache = load_cache()
    new_cache = {"kie": [], "fal": {}}
    check_fal(cache, new_cache)
    check_kie(cache, new_cache)
    save_cache(new_cache)

if __name__ == "__main__":
    check_updates()
