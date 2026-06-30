# Deployment Roadmap — tools.beez365.com/social-media-name-check

Target environment: **Azure App Service** (Linux, Python 3.12)
Target URL: `tools.beez365.com/social-media-name-check`
Audience: beez365.com users + anyone checking username availability for a new domain

---

## Phase 1 — Security hardening (do before any deployment)

### 1.1 Disable debug mode
- [ ] Move `debug=True` out of code
- [ ] Read from an environment variable: `DEBUG=false` in production, `DEBUG=true` locally
- [ ] Azure App Service injects env vars via Application Settings — no secrets in code

### 1.2 Rate limiting per IP
- [ ] Add `Flask-Limiter` dependency
- [ ] Limit `/check` endpoint to **10 requests per hour per IP**
- [ ] Rationale: a domain buyer realistically checks 5–10 names in a session; 10/hr is generous for legit use and hard to abuse
- [ ] Return a friendly `429 Too Many Requests` JSON response with a retry hint

### 1.3 Result caching
- [ ] Add `cachetools` (in-memory, no Redis needed for this scale)
- [ ] Cache check results for **30 minutes per username**
- [ ] If two visitors check `shinehubau` within 30 min, the second gets the cached result instantly
- [ ] Protects beez365.com server IP from being rate-limited or blacklisted by social platforms
- [ ] Cache is per-process (resets on restart) — acceptable for this use case

### 1.4 CORS lockdown
- [ ] Add `Flask-CORS` dependency
- [ ] Restrict the `/check` API to requests originating from `beez365.com` and `tools.beez365.com` only
- [ ] Prevents third parties from embedding or scraping this as a free backend service
- [ ] Allow `localhost` in development mode

### 1.5 HTTP security headers
- [ ] Add `Flask-Talisman` dependency
- [ ] Enables: `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`, `X-Content-Type-Options`
- [ ] Azure App Service provides HTTPS termination — Talisman enforces HTTPS redirect at app level too

---

## Phase 2 — Production server setup

### 2.1 Replace Flask dev server with Gunicorn
- [ ] Add `gunicorn` to `requirements.txt`
- [ ] Create `startup.txt` (Azure App Service startup command): `gunicorn --workers 2 --threads 4 --timeout 60 app:app`
- [ ] 2 workers × 4 threads = handles up to 8 concurrent checks without blocking
- [ ] 60s timeout covers slow platform responses

### 2.2 Environment configuration
- [ ] Create `.env.example` documenting all required variables (never commit real values)
- [ ] Variables needed:
  - `FLASK_ENV` — `production` or `development`
  - `DEBUG` — `false` in production
  - `ALLOWED_ORIGINS` — comma-separated list of allowed CORS origins
  - `RATE_LIMIT` — requests per hour per IP (default `10`)
  - `CACHE_TTL_MINUTES` — cache duration (default `30`)

---

## Phase 3 — Azure setup

### 3.1 Azure resources to create
- [ ] **Resource Group** — e.g. `rg-beez365-tools`
- [ ] **App Service Plan** — `B1` (Basic, ~$13/month) is sufficient; can scale up if needed
- [ ] **App Service** (Linux, Python 3.12) — e.g. `beez365-tools`
- [ ] No database, no storage account needed — app is stateless

### 3.2 Custom domain
- [ ] Add `tools.beez365.com` as a custom domain on the App Service
- [ ] Azure provides a free managed TLS certificate for custom domains (App Service Managed Certificate)
- [ ] Add a `CNAME` record in GoDaddy DNS: `tools` → `beez365-tools.azurewebsites.net`
- [ ] Sub-path `/social-media-name-check` handled by Flask routing (no extra Azure config needed)

### 3.3 Application Settings (environment variables)
- [ ] Set in Azure Portal → App Service → Configuration → Application Settings
- [ ] `FLASK_ENV=production`
- [ ] `DEBUG=false`
- [ ] `ALLOWED_ORIGINS=https://beez365.com,https://tools.beez365.com`
- [ ] `SCM_DO_BUILD_DURING_DEPLOYMENT=true` (tells Azure to run `pip install` on deploy)

### 3.4 Deployment method
- [ ] Recommended: **GitHub Actions** continuous deployment
  - Azure generates a publish profile secret → stored in GitHub repo secrets
  - Every push to `main` triggers a deploy automatically
- [ ] Alternative: deploy manually via Azure CLI (`az webapp deploy`) or VS Code Azure extension

---

## Phase 4 — UX improvements (optional, post-launch)

- [ ] **Pre-fill from URL param**: `tools.beez365.com/social-media-name-check?q=shinehubau`
  - User buys domain on GoDaddy → clicks a bookmarked link with the name pre-filled
- [ ] **Copy all available names** button — copies the list of available platforms for pasting into a notes doc
- [ ] **Shareable result link** — encode the username in the URL so results can be shared
- [ ] **Add more platforms**: Mastodon (mastodon.social), Bluesky, Threads (Meta)

---

## Summary of new dependencies to add

| Package | Purpose |
|---|---|
| `gunicorn` | Production WSGI server |
| `Flask-Limiter` | Per-IP rate limiting |
| `Flask-CORS` | Lock API to beez365.com origins |
| `Flask-Talisman` | HTTP security headers + HTTPS enforcement |
| `cachetools` | In-memory result caching |

Current dependencies (`flask`, `requests`) are unchanged.

---

## Risk: social platform ToS

Making automated HTTP requests to social media platforms is technically against most platforms' ToS.
Mitigations in place:
- **Caching** means we make at most 1 request per unique username per 30 minutes (not per user visit)
- **Rate limiting** caps total server-side requests to a low volume
- **Use case** is read-only, single-username lookup — minimal impact, comparable to a browser visit
- This is a tools site, not a bulk scraper

Recommendation: add a visible note on the page that results are for personal reference only.
