# Social Media Name Check

A local web tool that checks whether a username is available across the social media platforms. Enter a name once — the app queries all platforms concurrently and shows a consolidated result in seconds.

---

## What it covers

| Platform | Check method | Confidence |
|---|---|---|
| GitHub | Official API (200 / 404) | ✅ High |
| YouTube | HTTP status (404 = available) | ✅ High |
| Snapchat | HTTP status (404 = available) | ✅ High |
| TikTok | Embedded JSON `"statusCode":0` = taken | 🟡 Medium |
| Pinterest | Page title contains `\| Pinterest` = taken | 🟡 Medium |
| Twitch | Page title `Name - Twitch` pattern = taken | 🟡 Medium |
| Twitter / X | SSR page title ` / X` pattern = taken | 🟡 Medium |
| Instagram | Same HTML for all users — login required | 👁 Manual only |
| Facebook | Login wall — cannot automate | 👁 Manual only |
| LinkedIn | Login wall — cannot automate | 👁 Manual only |
| Reddit | Bot-verification wall for all requests | 👁 Manual only |

### How to read the results

| Status | Meaning |
|---|---|
| ✅ Available | No account found at that URL — name is likely free |
| ❌ Taken | An account was detected at that URL |
| ❓ Unknown | Platform returned an unexpected response (try again) |
| 👁 Check Manually | Automated check not possible — a direct link is provided |
| ⚠️ Error | Network timeout or connection failure |

> **Important:** Results are indicative, not guaranteed. Bot detection, CDN caching, and platform changes can affect accuracy. Always confirm availability directly on the platform before committing to a name.

### Why some platforms are manual-only

- **Instagram** — serves identical HTML for both existing and non-existing usernames; no profile data is embedded in the initial page without authentication.
- **Facebook / LinkedIn** — redirect all unauthenticated visitors to login pages.
- **Reddit** — returns a bot-verification challenge page for all automated requests since 2023.

---

## Install & run

**Requirements:** Python 3.9+

```bash
# 1. Clone the repo
git clone https://github.com/carmel-halabe/social-media-name-check.git
cd social-media-name-check

# 2. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Start the server
python app.py

# 4. Open in your browser
open http://127.0.0.1:5001
```

> **macOS note:** Port 5000 is used by AirPlay Receiver. The app runs on **port 5001** by default to avoid this conflict.

---

## Platform & tech stack

| | |
|---|---|
| Language | Python 3.9+ |
| Web framework | [Flask](https://flask.palletsprojects.com/) 3.x |
| HTTP client | [Requests](https://docs.python-requests.org/) 2.x |
| Concurrency | `concurrent.futures.ThreadPoolExecutor` (6 workers) |
| Frontend | Vanilla HTML + JavaScript, [Tailwind CSS](https://tailwindcss.com/) via CDN |
| Platforms checked | 11 (7 automated + 4 manual-link) |
