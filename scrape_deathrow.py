#!/usr/bin/env python3
# scrape_deathrow.py
# Option B – Directly request each inmate's detail page by ADC ID.

import csv
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_DETAIL = "https://inmatedatasearch.azcorrections.gov/DeathRowSearchInmateInfo.aspx?ID="
OUTPUT_CSV = "death_row_inmates.csv"
DELAY_BETWEEN = 1.5
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 🔹 You can expand or replace this list anytime.
INMATE_IDS = [
    "036085", "036366", "039656", "042891", "043800",
    "045659", "045676", "046561", "047079", "047398"
]

def get_inmate_fields(soup):
    """Extracts all labeled fields from the detail page."""
    def text(id_):
        tag = soup.find(id=id_)
        return tag.get_text(strip=True) if tag else ""
    img = soup.find("img", id="ImgIMNO_Crime")
    return {
        "adc_number": text("lblInmateNumber"),
        "name": text("lblName"),
        "comments": text("lblComments"),
        "proceedings": text("lblProceedings"),
        "aggravating": text("lblAggrave"),
        "mitigating": text("lblMitigate"),
        "pub_opinions": text("lblOpinion"),
        "mug_image": img["src"] if img and img.has_attr("src") else "",
    }

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    print("Starting direct scrape:", datetime.utcnow().isoformat() + "Z")

    all_rows = []

    for i, adc in enumerate(INMATE_IDS, start=1):
        url = BASE_DETAIL + adc
        print(f"[{i}/{len(INMATE_IDS)}] Fetching {url}")
        try:
            r = session.get(url, timeout=60)
            soup = BeautifulSoup(r.text, "html.parser")
            data = get_inmate_fields(soup)
            data["source_url"] = url
            data["scrape_time_utc"] = datetime.utcnow().isoformat() + "Z"
            all_rows.append(data)
        except Exception as e:
            print(f"⚠️ Error fetching {adc}: {e}")
        time.sleep(DELAY_BETWEEN)

    fieldnames = [
        "adc_number", "name", "comments", "proceedings",
        "aggravating", "mitigating", "pub_opinions", "mug_image",
        "source_url", "scrape_time_utc"
    ]
    print("Writing CSV:", OUTPUT_CSV)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"✅ Done. Scraped {len(all_rows)} inmate records.")
    print(f"CSV saved as {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
