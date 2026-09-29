from playwright.sync_api import sync_playwright
from openpyxl import Workbook, load_workbook
import random
import time
import os
import json

# ============================================================
# CONFIG - change stuff here instead of digging through the code
# ============================================================
MAX_PAGES_PER_SESSION = 99999   # how many pages to scrape in one run
MIN_DELAY = 4                   # min wait after each page (seconds)
MAX_DELAY = 8                   # max wait after each page (seconds)
MAX_RETRIES = 3                 # how many times to retry a failed page
PROGRESS_FILE = "scrape_progress.json"


# ============================================================
# HELPERS
# ============================================================

def load_progress():
    """
    Checks if there's an old progress file lying around.
    If yes, we know where we left off last time so we don't
    start from page 1 again like idiots.
    """
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    # first time running, no progress yet
    return {"last_completed_page": 0, "category": None}


def save_progress(category, page_no):
    # just dumps current position to file after every page
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"last_completed_page": page_no, "category": category}, f)


def safe_get_text(card, selector, default="N/A"):
    """
    Some product cards don't have rating/sold/origin etc.
    Instead of crashing every time one is missing, just return
    a default value. Saves a LOT of headache.
    """
    locator = card.locator(selector)
    if locator.count() > 0:
        return locator.inner_text()
    return default


def scrape_single_page(page):
    # wait for products to actually show up, 30 sec timeout
    page.wait_for_selector("[data-qa-locator='product-item']", timeout=30000)

    cards = page.locator("[data-qa-locator='product-item']").all()
    rows = []

    for card in cards:
        # name and price should always be there
        name = card.locator(".RfADt a").get_attribute("title")
        price = card.locator(".ooOxS").inner_text()

        # these might not exist on every card, hence safe_get_text
        origin = safe_get_text(card, ".oa6ri", default="N/A")
        star_review_count = safe_get_text(card, ".qzqFw", default="")
        sold = safe_get_text(card, "._1cEkb", default="N/A")

        # counting filled stars, Dy1nx = filled star class
        filled_star_count = card.locator("._9-ogB.Dy1nx").count()
        star_text = "\u2605" * filled_star_count
        stars_given = star_text + star_review_count

        rows.append([name, price, sold, stars_given, origin])

    return rows


def scrape_page_with_retry(page, page_no):
    """
    Tries scraping a page, and if it fails (captcha, random glitch,
    whatever) it retries a few times. Gives you a chance to solve
    captcha manually before it tries again.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            rows = scrape_single_page(page)
            return rows  # worked, just return it

        except Exception as e:
            print(f"Page {page_no}: attempt {attempt}/{MAX_RETRIES} failed.")
            print(f"   reason: {e}")

            if attempt < MAX_RETRIES:
                print("   if there's a captcha or popup, solve it now.")
                input("   press Enter once solved to retry...")

                # backoff - wait a bit longer each retry (5s, 10s, 15s...)
                backoff_wait = attempt * 5
                print(f"   waiting {backoff_wait}s before retrying...")
                time.sleep(backoff_wait)
            else:
                print(f"page {page_no} failed {MAX_RETRIES} times, skipping it.")
                return []


# ============================================================
# MAIN
# ============================================================

def run_scraper():
    with sync_playwright() as p:
        # headless=False on purpose so you can see + solve captchas
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # check if we already scraped something before
        progress = load_progress()

        page.goto("https://www.daraz.pk/", wait_until="domcontentloaded", timeout=0)

        # in case a verification popup shows up right away
        input("solve captcha/popup if there is one, otherwise just press Enter...")

        category = input("What category you want to scrape from Daraz: ")

        # resume from last time if same category
        start_page = 1
        if progress["category"] == category and progress["last_completed_page"] > 0:
            resume_choice = input(
                f"last time we got to page {progress['last_completed_page']} for '{category}'. "
                f"resume from there? (y/n): "
            )
            if resume_choice.lower() == "y":
                start_page = progress["last_completed_page"] + 1

        # search for the category
        search_bar = page.locator("input[name='q']")
        search_bar.click()
        search_bar.type(category)
        search_bar.press("Enter")

        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # excel file setup - new one or append to existing
        filename = f"daraz_{category}.xlsx"

        if start_page > 1 and os.path.exists(filename):
            wb = load_workbook(filename)
            sheet = wb.active
            print(f"opened existing file '{filename}', appending new data.")
        else:
            wb = Workbook()
            sheet = wb.active
            sheet.title = category[:31]  # excel sheet names max 31 chars
            sheet.append(["Product Name", "Price", "Sold", "Stars", "Origin"])

        # figure out how many pages of results there are
        page.wait_for_selector(".e5J1n a")
        last_page_text = page.locator(".e5J1n a").last.inner_text()
        last_page = int(last_page_text)

        print(f"total pages available: {last_page}")

        end_page = min(start_page + MAX_PAGES_PER_SESSION - 1, last_page)
        print(f"scraping page {start_page} to {end_page} this session")

        # go through pages one by one
        for page_no in range(start_page, end_page + 1):
            print(f"\n--- scraping page {page_no} ---\n")

            if page_no > start_page or start_page > 1:
                url = f"https://www.daraz.pk/catalog/?q={category}&page={page_no}"
                page.goto(url, wait_until="domcontentloaded", timeout=0)

                # random delay so it doesn't look like a bot hammering the site
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                print(f"waiting {delay:.1f}s...")
                time.sleep(delay)

            rows = scrape_page_with_retry(page, page_no)

            for row in rows:
                sheet.append(row)

            print(f"page {page_no}: found {len(rows)} products")

            # save after every page so we never lose data
            wb.save(filename)

            save_progress(category, page_no)
            print(f"progress saved up to page {page_no}")

        print(f"\ndone! file saved as: {filename}")
        print("run the script again if you want more pages, it'll resume automatically.")

        browser.close()

run_scraper()
