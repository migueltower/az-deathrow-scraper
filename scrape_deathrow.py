#!/usr/bin/env python3
# scrape_deathrow.py
# Requires: playwright
# Usage: python scrape_deathrow.py

import csv
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

MAIN_PAGE = "https://corrections.az.gov/death-row"
INMATE_DOMAIN_PART = "inmatedatasearch.azcorrections.gov"
OUTPUT_CSV = "death_row_inmates.csv"
DELAY_BETWEEN = 1.5

FIELD_SELECTORS = {
    "adc": "#lblInmateNumber",
    "name": "#lblName",
    "proceedings": "#lblProceedings",
    "aggravating": "#lblAggrave",
    "mitigating": "#lblMitigate",
    "public_opinion": "#lblOpinion",
    "mug_image": "#ImgIMNO_Crime",
}

def text_or_empty(page, selector):
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
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()

        print("Loading main page:", MAIN_PAGE)
        page.goto(MAIN_PAGE, timeout=60000)
        time.sleep(1)

        anchors = page.query_selector_all("a[href]")
        links = []
        for a in anchors:
            href = a.get_attribute("href") or ""
            if not href:
                continue
            full = urljoin(MAIN_PAGE, href)
            if "DeathRowSearch.aspx" in full or INMATE_DOMAIN_PART in urlparse(full).netloc:
                if full not in links:
                    links.append(full)

        if not links:
            print("No inmate links found on main page. Trying the dedicated search host...")
            search_root = "https://inmatedatasearch.azcorrections.gov/DeathRowSearch.aspx"
            page.goto(search_root, timeout=60000)
            time.sleep(1)
            anchors = page.query_selector_all("a[href]")
            for a in anchors:
                href = a.get_attribute("href") or ""
                full = urljoin(search_root, href)
                if "DeathRowSearch.aspx" in full and full not in links:
                    links.append(full)

        print(f"Found {len(links)} candidate inmate links")

        for idx, link in enumerate(links, start=1):
            try:
                print(f"[{idx}/{len(links)}] Visiting: {link}")
                page.goto(link, timeout=60000)
                page.wait_for_timeout(500)
                data = {}
                for key, selector in FIELD_SELECTORS.items():
                    data[key] = text_or_empty(page, selector)
                data["source_url"] = link
                data["scrape_time_utc"] = datetime.utcnow().isoformat() + "Z"
                rows.append(data)
                time.sleep(DELAY_BETWEEN)
            except Exception as e:
                print("  ERROR visiting", link, ":", str(e))
                continue

        browser.close()

    fieldnames = [
        "adc", "name", "proceedings", "aggravating", "mitigating",
        "public_opinion", "mug_image", "source_url", "scrape_time_utc"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    print("Done. Rows scraped:", len(rows))

if __name__ == "__main__":
    main()
