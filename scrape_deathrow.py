#!/usr/bin/env python3
# scrape_deathrow.py
# Uses Playwright headless Chromium to pass Cloudflare and extract Death Row inmate data.

import csv
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

MAIN_URL = "https://inmatedatasearch.azcorrections.gov/DeathRowSearch.aspx"
OUTPUT_CSV = "death_row_inmates.csv"
DELAY = 1.5  # seconds between inmate clicks

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

def get_text(page, selector):
    try:
        el = page.query_selector(selector)
        if not el:
            return ""
        tag = el.evaluate("el => el.tagName.toLowerCase()")
        return el.get_attribute("src") if tag == "img" else el.inner_text().strip()
    except Exception:
        return ""

def scrape():
    print("Starting scrape:", datetime.utcnow().isoformat() + "Z")
    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        # Step 1. Open the main Death Row page (Cloudflare passes automatically)
        print("Opening:", MAIN_URL)
        page.goto(MAIN_URL, timeout=90000)
        page.wait_for_selector("#GVDeathRow")

        total = 0
        page_num = 1

        while True:
            print(f"📄 Page {page_num}")
            inmates = page.query_selector_all("#GVDeathRow a[id*='CrimeInfo']")
            print(f"  Found {len(inmates)} inmate links.")

            for i, link in enumerate(inmates, start=1):
                try:
                    print(f"    [{i}/{len(inmates)}] Opening inmate detail...")
                    link.click()
                    page.wait_for_selector("#lblInmateNumber", timeout=60000)

                    data = {k: get_text(page, s) for k, s in FIELD_SELECTORS.items()}
                    data["source_url"] = page.url
                    data["scrape_time_utc"] = datetime.utcnow().isoformat() + "Z"
                    rows.append(data)

                    # Return to list
                    back = page.query_selector("#btnBackFromCrime")
                    if back:
                        back.click()
                        page.wait_for_selector("#GVDeathRow", timeout=60000)

                    time.sleep(DELAY)
                except Exception as e:
                    print("❌ Error:", e)
                    continue

            # Next page?
            next_link = page.query_selector("a[href*='Page$" + str(page_num + 1) + "']")
            if next_link:
                print("➡️  Going to next page...")
                next_link.click()
                page.wait_for_selector("#GVDeathRow", timeout=60000)
                page_num += 1
                time.sleep(1)
            else:
                break

        browser.close()

    # Write CSV
    fieldnames = list(FIELD_SELECTORS.keys()) + ["source_url", "scrape_time_utc"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"✅ Done. {len(rows)} inmates scraped.")
    print(f"CSV saved as {OUTPUT_CSV}")

if __name__ == "__main__":
    scrape()
