# Telegram Price Tracker

Scrapes public Telegram channels for construction/steel prices in Iran and logs them to a Google Sheet — automatically, every day via GitHub Actions.

## How it works

1. Fetches each channel's public page at `https://t.me/s/<channel>`
2. Parses messages with BeautifulSoup
3. Extracts prices using regex (Persian + English numerals, commas, Toman/Rial keywords)
4. Appends new rows to a Google Sheet (deduplicates by message link)

## Tracked channels

| Channel | Topic |
|---|---|
| @bazarfelez | Steel market |
| @tasisat_mechanic_sakhteman | Mechanical/building installations |
| @civilmashhadd | Civil engineering (Mashhad) |
| @civilejra | Civil execution |
| @atifoolad | Ati Steel |
| @PipeBazaar | Pipe market |
| @mihansazan | Mihan builders |
| @Bahrami_Steel | Bahrami Steel |

## Google Sheet columns

| Column | Description |
|---|---|
| Date | Message publish date (YYYY-MM-DD) |
| Channel | Channel handle (e.g. @bazarfelez) |
| Price | Extracted price value |
| Full_Message | Full message text (up to 1000 chars) |
| Message_Link | Direct link to the Telegram message |
| Extracted_At | Timestamp when the row was written |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd telegram-price-tracker
```

### 2. Create a Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts** → Create service account
5. Give it any name, click through the steps
6. Click the service account → **Keys** tab → **Add Key** → **JSON**
7. Save the downloaded file as `credentials.json` in this folder

### 3. Share your Google Sheet with the service account

1. Create a new Google Sheet (or use an existing one)
2. Copy the service account email (looks like `name@project.iam.gserviceaccount.com`)
3. Share the sheet with that email as **Editor**

### 4. Configure

Edit `config.py` to change:
- `CHANNELS` — add/remove channel handles
- `GOOGLE_SHEET_NAME` — name of your Google Sheet
- `MAX_MESSAGES_PER_CHANNEL` — how many recent messages to scan

Or set environment variables (see `config.py` for names).

### 5. Run locally

```bash
pip install -r requirements.txt
python main.py
```

---

## GitHub Actions setup (automated daily runs)

### Add these secrets in your GitHub repo

Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|---|---|
| `GOOGLE_CREDENTIALS_JSON` | The full contents of your `credentials.json` file |
| `GOOGLE_SHEET_NAME` | Name of your Google Sheet |
| `HTTP_PROXY` | *(optional)* HTTP proxy URL, e.g. `http://user:pass@host:port` |
| `HTTPS_PROXY` | *(optional)* HTTPS proxy URL |

### Schedule

The workflow runs daily at **07:00 Tehran time (03:30 UTC)**. To change the schedule, edit the `cron` line in `.github/workflows/price-tracker.yml`.

You can also trigger a run manually from the **Actions** tab → **Telegram Price Tracker** → **Run workflow**.

---

## Proxy / VPN support

If GitHub Actions IPs are blocked, set `HTTP_PROXY` and `HTTPS_PROXY` secrets to a working proxy URL. The script passes these through to every HTTP request automatically.

Alternatively, you can self-host this on a VPS inside Iran or use a residential proxy service.

---

## Upgrading to Telethon (optional)

The scraper is structured so you can swap `fetch_channel_page` + `parse_messages` in `main.py` with a Telethon-based implementation later without touching the Google Sheets logic. Just replace the scraping layer in those two functions.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SpreadsheetNotFound` | Make sure the sheet name in `GOOGLE_SHEET_NAME` matches exactly, and the sheet is shared with the service account email |
| `credentials.json` not found | Check the file path; set `CREDENTIALS_FILE` env var if it's elsewhere |
| No prices extracted | The channel may use image-only posts or an unusual price format — check `price_tracker.log` and adjust patterns in `main.py` |
| SSL errors | A proxy is likely needed; set `HTTP_PROXY` / `HTTPS_PROXY` |
| Rate limited by Telegram | Increase `DELAY_BETWEEN_CHANNELS` in `config.py` |
