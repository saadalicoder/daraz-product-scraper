# Daraz Product Scraper

A Python script that scrapes product listings from Daraz.pk (name, price, sold count, rating, origin) and saves everything into an Excel file. Built with Playwright.

## Why I made this

Needed a way to pull product data from Daraz for a specific category without manually copy-pasting stuff for hours. Also wanted something that wouldn't just die the moment a captcha showed up.

## Features

- Scrapes name, price, sold count, star rating, and origin for each product
- Saves results to an `.xlsx` file automatically
- Handles missing fields (not every product has a rating/origin) without crashing
- Retries a page a few times if something goes wrong instead of just quitting
- Saves progress after every page - if the script crashes or you close it, running it again picks up where you left off instead of starting over
- Random delays between pages so it's not hammering the site like a bot

## Requirements

- Python 3.9+
- Google Chrome / Chromium (installed automatically by Playwright, see below)

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python scraper.py
```

The script will:
1. Open a browser window (not headless, on purpose - see note below)
2. Ask you to solve a captcha manually if one pops up
3. Ask which category you want to scrape
4. If you've scraped that category before, it'll ask if you want to resume from where you left off
5. Start scraping pages and saving to `daraz_<category>.xlsx`

## Notes / Known limitations

- Captcha solving is manual. When one shows up, the script pauses and waits for you to solve it in the browser window, then you hit Enter to continue. No auto-solving here.
- The script runs with `headless=False` on purpose so you can actually see and solve captchas when they pop up.
- CSS selectors (`.RfADt`, `.ooOxS`, etc.) are tied to Daraz's current site structure. If Daraz redesigns their frontend, these will break and need to be updated - inspect the page again and swap in the new selectors.
- No proxy rotation. If you scrape a lot of pages back to back you'll probably run into captchas more often. The retry logic + manual solve handles this but it's not fully hands-off.
- Only tested against daraz.pk, not other Daraz regional sites.

## To-do (maybe)

- Auto-detect selector changes and warn instead of crashing
- Add logging to a file instead of just printing to console
- Look into proxy support for longer scraping sessions
