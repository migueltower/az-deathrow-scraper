#!/usr/bin/env python3
# scrape_deathrow.py
# Scrapes Arizona DOC Death Row inmate data by emulating ASP.NET postbacks.

import csv
import time
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://inmatedatasearch.azcorrections.gov/DeathRowSearch.aspx"
OUTPUT_CSV = "death_row_inmates.csv"
DELAY_BETWEEN = 1.5  # seconds between inmates
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_hidden_fields(soup):
    """Extracts ASP.NET hidden form fields required for postbacks."""
    fields = {}
    for key in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
        tag = soup.find("input", {"name": key})
        fields[key] = tag["value"] if tag and "value" in tag.attrs else ""
    return fields

def get_inmate_fields(soup):
    """Extracts inmate details from the detail page."""
    def get_text(id_):
        el = soup.find(id=id_)
        return el.get_text(strip=True) if el else ""
    img = soup.find("img", id="ImgIMNO_Crime")
    return {
        "adc_number": get_text("lblInmateNumber"),
        "name": get_text("lblName"),
        "comments": get_text("lblComments"),
        "proceedings": get_text("lblProceedings"),
        "aggravating": get_text("lblAggrave"),
        "mitigating": get_text("lblMitigate"),
        "pub_opinions": get_text("lblOpinion"),
        "mug_image": img["src"] if img and img.has_attr("src") else "",
    }

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Starting scraper:", datetime.utcnow().isoformat() + "Z")

    resp = session.get(BASE_URL, timeout=60)
    soup = BeautifulSoup(resp.text, "html.parser")
    hidden = get_hidden_fields(soup)

    # Find all inmate link elements (the 'CrimeInfo' links)
    links = soup.select("#GVDeathRow a[href*='CrimeInfo']")
    if not links:
        # Try fallback search using regex
        links = soup.find_all("a", href=re.compile("CrimeInfo"))
    print(f"Found {len(links)} inmate links on this page.")

    inmates = []

    for i, link in enumerate(links, start=1):
        # Extract the __doPostBack argument (e.g. GVDeathRow$ctl03$CrimeInfo)
        href = link.get("href", "")
        match = re.search(r"__doPostBack\('([^']+)'", href)
        if not match:
            continue
        event_target = match.group(1)
        print(f"[{i}/{len(links)}] Fetching inmate with EVENTTARGET={event_target}")

        # Prepare POST data for __doPostBack
        post_data = {
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
            **hidden,
        }

        detail = session.post(BASE_URL, data=post_data, headers=HEADERS, timeout=60)
        detail_soup = BeautifulSoup(detail.text, "html.parser")
        inmate_data = get_inmate_fields(detail_soup)
        inmate_data["source_url"] = BASE_URL
        inmate_data["scrape_time_utc"] = datetime.utcnow().isoformat() + "Z"
        inmates.append(inmate_data)

        time.sleep(DELAY_BETWEEN)

        # Refresh main list and hidden fields between iterations
        resp = session.get(BASE_URL, timeout=60)
        soup = BeautifulSoup(resp.text, "html.parser")
        hidden = get_hidden_fields(soup)

    # Write CSV
    fieldnames = [
        "adc_number", "name", "comments", "proceedings",
        "aggravating", "mitigating", "pub_opinions", "mug_image",
        "source_url", "scrape_time_utc",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in inmates:
            writer.writerow(r)

    print(f"✅ Done. Scraped {len(inmates)} inmate records.")
    print(f"CSV saved as {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
