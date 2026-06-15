# Wedding Venue Scraper

Automatically searches for UK wedding venues daily, extracts details with
Claude, tracks new finds, and emails you a summary when something new shows up.

## How it works

1. **Discovery** – Claude runs web searches (see `SEARCH_QUERIES` in `scraper.py`)
2. **Extraction** – For each new result, Claude pulls out name, location,
   capacity, price range, and a summary
3. **Tracking** – Results are stored in `venues.json`, committed back to the repo
4. **Notification** – If anything new was found, you get an email

It runs automatically every day via GitHub Actions — no server needed.

---

## Setup (one-time, ~15 minutes)

### 1. Create a GitHub repo
- Create a new **private** repo on GitHub (e.g. `wedding-venue-scraper`)
- Upload these files to it: `scraper.py`, `requirements.txt`,
  `.github/workflows/venue-scraper.yml`

### 2. Get an Anthropic API key
- Go to https://console.anthropic.com
- Create an API key (Settings → API Keys)
- You'll add this as a secret in step 4

### 3. Set up email sending (Gmail example)
- Use a Gmail account (a dedicated one is cleanest, but your own works too)
- Go to https://myaccount.google.com/apppasswords and create an **App Password**
  (requires 2-factor authentication to be enabled on the account)
- Note down: your Gmail address, and the generated 16-character app password

### 4. Add secrets to your GitHub repo
Go to **Repo → Settings → Secrets and variables → Actions → New repository secret**,
and add each of these:

| Secret name         | Value                                      |
|----------------------|--------------------------------------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key                      |
| `SMTP_HOST`         | `smtp.gmail.com`                            |
| `SMTP_PORT`         | `587`                                       |
| `SMTP_USER`         | Your Gmail address                          |
| `SMTP_PASS`         | The 16-character app password from step 3   |
| `NOTIFY_EMAIL`      | The email address you want alerts sent to   |

### 5. Run it
- Go to the **Actions** tab in your repo
- Select "Wedding Venue Scraper" → **Run workflow** (this triggers it manually
  for the first time — no need to wait for the schedule)
- After a minute or two, check your email and check that `venues.json` has been
  created/updated in the repo

It will now run automatically every day at 08:00 UTC. To change the time or
frequency, edit the `cron` line in `.github/workflows/venue-scraper.yml`
(use https://crontab.guru to build a schedule expression).

---

## Customising the search

Edit `SEARCH_QUERIES` in `scraper.py` to narrow things down — for example:

```python
SEARCH_QUERIES = [
    "wedding venues Surrey availability 2026",
    "wedding venues Hampshire under 100 guests",
    "barn wedding venue Kent now booking 2027",
]
```

You can add as many queries as you like, but each one costs API calls — start
with 3-5 and expand once you've checked it's working as expected.

## Cost

Each run makes roughly:
- 1 search call per query in `SEARCH_QUERIES`
- 1 extraction call per *new* result found

With Claude Sonnet 4.6, a daily run with ~4 queries typically costs a small
fraction of a cent to a few cents per day, depending on how many new venues
turn up. Check current pricing at https://docs.claude.com.

## Troubleshooting

- **No email arriving**: check the Actions tab → click the latest run → expand
  the "Run scraper" step for errors. Common causes: wrong app password, or
  Gmail blocking the login (check for a security alert email from Google).
- **`venues.json` not updating**: make sure the workflow has `permissions:
  contents: write` (already included) and that Actions has write access
  (Repo → Settings → Actions → General → Workflow permissions).
- **Getting too many/irrelevant results**: tighten `SEARCH_QUERIES` to be more
  specific (region, capacity, date).
