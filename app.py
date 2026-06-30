import re
import concurrent.futures
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Browser-like headers to reduce bot detection
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}

# Platforms to check. Each entry defines how availability is determined.
#
# check: "http"   → HTTP status + optional content check
#        "api"    → same but sends JSON Accept header (GitHub)
#        "manual" → cannot be reliably automated; show a manual-check link
#
# content_check.taken_strings:
#   When a 200 is returned, search the response body for these strings.
#   If ANY match → TAKEN.  If none match → AVAILABLE.
#   Omit (or leave empty) to treat all 200s as TAKEN.
PLATFORMS = [
    # ── Manual-only (login walls or identical HTML for all users) ─────────────
    {
        "name": "Instagram",
        "url": None,
        "profile_url": "https://www.instagram.com/{}/",
        "emoji": "📸",
        "color": "#E1306C",
        "confidence": "manual",
        "note": "Hugely popular with all migrant communities — same HTML for existing and non-existing users; login required to verify",
        "check": "manual",
    },
    {
        "name": "Facebook",
        "url": None,
        "profile_url": "https://www.facebook.com/{}",
        "emoji": "👥",
        "color": "#1877F2",
        "confidence": "manual",
        "note": "#1 platform for migrant communities in Australia — requires login to verify",
        "check": "manual",
    },
    {
        "name": "LinkedIn",
        "url": None,
        "profile_url": "https://www.linkedin.com/in/{}",
        "emoji": "💼",
        "color": "#0A66C2",
        "confidence": "manual",
        "note": "Essential for professional migrants and job seekers — requires login to verify",
        "check": "manual",
    },
    {
        "name": "Reddit",
        "url": None,
        "profile_url": "https://www.reddit.com/user/{}/",
        "emoji": "👾",
        "color": "#FF4500",
        "confidence": "manual",
        "note": "Active in r/australia, r/AusVisa, r/Melbourne, r/Sydney — bot-verification wall prevents automated check",
        "check": "manual",
    },
    # ── HTTP status code checks (reliable) ────────────────────────────────────
    {
        "name": "GitHub",
        "url": "https://api.github.com/users/{}",
        "profile_url": "https://github.com/{}",
        "emoji": "🐙",
        "color": "#333333",
        "confidence": "high",
        "note": "Tech community — many migrants work in Australia's IT sector",
        "check": "api",
        "available": [404],
        "taken": [200],
    },
    {
        "name": "Snapchat",
        "url": "https://www.snapchat.com/add/{}",
        "profile_url": "https://www.snapchat.com/add/{}",
        "emoji": "👻",
        "color": "#FFFC00",
        "confidence": "high",
        "note": "Popular with younger demographic",
        "check": "http",
        "available": [404],
        "taken": [200],
    },
    {
        "name": "YouTube",
        "url": "https://www.youtube.com/@{}",
        "profile_url": "https://www.youtube.com/@{}",
        "emoji": "▶️",
        "color": "#FF0000",
        "confidence": "high",
        "note": "Content creation, community vlogs, migrant support channels",
        "check": "http",
        "available": [404],
        "taken": [200],
    },
    # ── Content-based checks (200 for all users; use page content to decide) ──
    {
        # Real user title:  "Elon Musk (@elonmusk) / X"
        # Fake user title:  (no title — JS-only render)
        "name": "Twitter / X",
        "url": "https://x.com/{}",
        "profile_url": "https://x.com/{}",
        "emoji": "🐦",
        "color": "#000000",
        "confidence": "medium",
        "note": "News, advocacy, and public discourse",
        "check": "http",
        "available": [404],
        "taken": [200],
        "content_check": {
            "taken_strings": [" / X"],
        },
    },
    {
        # Real user: embedded JSON has "statusCode":0
        # Fake user: embedded JSON has "statusCode":10221 (or other non-zero)
        "name": "TikTok",
        "url": "https://www.tiktok.com/@{}",
        "profile_url": "https://www.tiktok.com/@{}",
        "emoji": "🎵",
        "color": "#010101",
        "confidence": "medium",
        "note": "Fast-growing with younger migrant communities",
        "check": "http",
        "available": [404],
        "taken": [200],
        "content_check": {
            "taken_strings": ['"statusCode":0'],
        },
    },
    {
        # Real user title:  "Name (user) - Profile | Pinterest"
        # Fake user title:  (empty / no profile info)
        "name": "Pinterest",
        "url": "https://www.pinterest.com/{}/",
        "profile_url": "https://www.pinterest.com/{}/",
        "emoji": "📌",
        "color": "#E60023",
        "confidence": "medium",
        "note": "Lifestyle, food, and creative communities",
        "check": "http",
        "available": [404],
        "taken": [200],
        "content_check": {
            "taken_strings": ["| Pinterest"],
        },
    },
    {
        # Real user title:  "Ninja - Twitch"
        # Fake user title:  "Twitch"  (no " - " prefix)
        "name": "Twitch",
        "url": "https://www.twitch.tv/{}",
        "profile_url": "https://www.twitch.tv/{}",
        "emoji": "🎮",
        "color": "#9146FF",
        "confidence": "medium",
        "note": "Gaming and live-streaming community",
        "check": "http",
        "available": [404],
        "taken": [200],
        "content_check": {
            "taken_strings": [" - Twitch"],
        },
    },
]

# Only allow safe username characters; prevents SSRF via URL injection
USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,50}$")


def check_platform(platform: dict, username: str) -> dict:
    base = {
        "name": platform["name"],
        "emoji": platform["emoji"],
        "color": platform["color"],
        "profile_url": platform["profile_url"].format(username),
        "confidence": platform["confidence"],
        "note": platform["note"],
    }

    if platform["check"] == "manual":
        return {**base, "status": "manual"}

    url = platform["url"].format(username)
    headers = dict(REQUEST_HEADERS)
    if platform["check"] == "api":
        headers["Accept"] = "application/json"

    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        code = resp.status_code

        if code in platform.get("available", []):
            return {**base, "status": "available"}

        if code in platform.get("taken", []):
            taken_strings = platform.get("content_check", {}).get("taken_strings", [])
            if taken_strings:
                # Platform returns 200 for both existing and non-existing users.
                # Only mark as TAKEN if a known "profile exists" string is found.
                if any(s in resp.text for s in taken_strings):
                    return {**base, "status": "taken"}
                return {**base, "status": "available"}
            # No content check needed — 200 reliably means taken.
            return {**base, "status": "taken"}

        return {**base, "status": "unknown"}

    except requests.Timeout:
        return {**base, "status": "error", "error": "Request timed out"}
    except requests.RequestException:
        return {**base, "status": "error", "error": "Connection failed"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400
    if not USERNAME_RE.match(username):
        return jsonify({
            "error": (
                "Username may only contain letters, numbers, dots (.), "
                "hyphens (-), and underscores (_) — max 50 characters."
            )
        }), 400

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(check_platform, p, username): p for p in PLATFORMS}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda x: x["name"])
    return jsonify({"username": username, "results": results})


if __name__ == "__main__":
    # debug=False in any public deployment
    app.run(debug=True, port=5001)
