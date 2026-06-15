"""
Wedding Venue Scraper
----------------------
1. Searches the web for UK wedding venues using Claude's web_search tool.
2. Extracts structured details (name, location, capacity, price) using Claude.
3. Compares against previously seen venues (stored in venues.json).
4. Emails a summary of NEW venues found since the last run.

Run on a schedule (see .github/workflows/venue-scraper.yml).
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
import anthropic

# ---------- CONFIG ----------
DATA_FILE = "venues.json"

# Edit these search queries to refine what you're looking for.
SEARCH_QUERIES = [
    "new wedding venues UK 2026 availability",
    "wedding venue open days UK announced",
    "barn wedding venue UK now booking",
    "country house wedding venue UK availability 2026",
]

MODEL = "claude-sonnet-4-6"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


# ---------- STEP 1: DISCOVERY ----------
def search_for_venues(query):
    """Run a web search via Claude and return a list of result URLs + titles."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        messages=[{"role": "user", "content": f"Search for: {query}"}],
    )

    results = []
    for block in response.content:
        if block.type == "web_search_tool_result":
            for item in block.content:
                if hasattr(item, "url"):
                    results.append({"url": item.url, "title": getattr(item, "title", "")})
    return results


# ---------- STEP 2: EXTRACTION ----------
def extract_venue_details(url, title):
    """Ask Claude to summarise/extract structured venue info from a URL."""
    prompt = f"""You are helping build a database of UK wedding venues.

Given this URL and title, use web search if needed to find details about the venue.
Respond with ONLY a JSON object (no markdown, no extra text) with these fields:
- name (string)
- location (string, town/region)
- capacity (string, e.g. "up to 150 guests", or null if unknown)
- price_range (string, e.g. "from £5,000", or null if unknown)
- summary (1 sentence description)

URL: {url}
Title: {title}
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}],
        messages=[{"role": "user", "content": prompt}],
    )

    # Find the final text block (the JSON answer)
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        return None

    raw = text_blocks[-1].strip()
    # Strip accidental markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


# ---------- STEP 3: STORAGE / DEDUPE ----------
def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_all(venues):
    with open(DATA_FILE, "w") as f:
        json.dump(venues, f, indent=2)


# ---------- STEP 4: EMAIL ----------
def send_email(new_venues):
    if not new_venues:
        print("No new venues found — skipping email.")
        return

    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    to_email = os.environ["NOTIFY_EMAIL"]

    lines = []
    for v in new_venues:
        lines.append(
            f"- {v['details'].get('name', 'Unknown')} "
            f"({v['details'].get('location', '?')})\n"
            f"  Capacity: {v['details'].get('capacity', '?')} | "
            f"Price: {v['details'].get('price_range', '?')}\n"
            f"  {v['details'].get('summary', '')}\n"
            f"  {v['url']}\n"
        )

    body = f"Found {len(new_venues)} new wedding venue(s):\n\n" + "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"Wedding Venue Scraper: {len(new_venues)} new result(s)"
    msg["From"] = smtp_user
    msg["To"] = to_email

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())

    print(f"Email sent to {to_email} with {len(new_venues)} new venue(s).")


# ---------- MAIN ----------
def main():
    existing = load_existing()
    new_venues = []

    seen_urls = set()
    for query in SEARCH_QUERIES:
        print(f"Searching: {query}")
        for result in search_for_venues(query):
            url = result["url"]
            if url in seen_urls or url in existing:
                continue
            seen_urls.add(url)

            print(f"  Extracting: {url}")
            details = extract_venue_details(url, result["title"])
            if not details:
                continue

            existing[url] = details
            new_venues.append({"url": url, "details": details})

    save_all(existing)
    send_email(new_venues)
    print(f"Done. {len(new_venues)} new venue(s) added. {len(existing)} total tracked.")


if __name__ == "__main__":
    main()
