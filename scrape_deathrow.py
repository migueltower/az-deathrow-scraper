#!/usr/bin/env python3
# scrape_deathrow.py
# Updated version: includes Comments field, ensures blanks are written,
# and more reliable navigation for each inmate page.

import csv
import time
from datetime import datetime
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

MAIN_PAGE = "https://inmatedatasearch.azcorrections.gov/DeathRowSearch.aspx"
OUTPUT_CSV = "death_row_inmates.csv"
DELAY_BETWEEN = 2  # seconds between inmate visits

# These are the element IDs found in your sample HTML
FIELD_SELECTORS = {
    "adc_number": "#lblInmateNumber",
    "name": "#lblName",
    "comments": "#lblComments",
    "proceedings": "#lblProceedings",
    "aggravating": "#lblAggrave",
    "mitigating": "#lblMitigate",
    "pub_opinions": "#lblOpinion",
    "mug_image": "#ImgIMNO_Crime",
}

def text_or_empty(page, selector):
    """Return the inner text or image URL for the given selector."""
    try:
        el = page.query_selector(selector)
        if not el:
            return ""
        tag = el.evaluate("el => el.tagName.toLowerCase()")
        if tag == "img":
            src = el.get_attribute("src") or ""
            return src
        return el.inner_text().strip()
    except Exception:
        return ""

def main():
    print("Starting scraper:", datetime.utcnow().isoformat() + "Z")
    all_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()

        # Step 1. Go to the main list page
        print("Loading main list:", MAIN_PAGE)
        page.goto(MAIN_PAGE, timeout=90000)
        time.sleep(2)

        # Step 2. Find all inmate detail links
        inmate_links = []
        for a in page.query_selector_all("a[href]"):
            href = a.get_attribute("href") or ""
            if "DeathRowSearch.aspx" in href and "ID=" in href:
                full_url = urljoin(MAIN_PAGE, href)
                if full_url not in inmate_links:
                    inmate_links.append(full_url)

        print(f"Found {len(inmate_links)} inmate links.")
        if not inmate_links:
            print("⚠️ No inmate links found — site layout may have changed.")
            return

        # Step 3. Visit each inmate page
        for idx, link in enumerate(inmate_links, 1):
            print(f"[{idx}/{len(inmate_links)}] Visiting: {link}")
            try:
                page.goto(link, timeout=90000)
                time.sleep(1.5)

                row = {}
                for field, selector in FIELD_SELECTORS.items():
                    row[field] = text_or_empty(page, selector)

                row["source_url"] = link
                row["scrape_time_utc"] = datetime.utcnow().isoformat() + "Z"
                all_rows.append(row)
            except Exception as e:
                print("❌ Error on", link, ":", e)
            time.sleep(DELAY_BETWEEN)

        browser.close()

    # Step 4. Write CSV (always includes all fields)
    fieldnames = list(FIELD_SELECTORS.keys()) + ["source_url", "scrape_time_utc"]
    print("Writing CSV:", OUTPUT_CSV)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            clean_row = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(clean_row)

    print("✅ Done. Total inmates scraped:", len(all_rows))

if __name__ == "__main__":
    main()
