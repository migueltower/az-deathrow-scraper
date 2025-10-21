#!/usr/bin/env python3
# scrape_deathrow.py
# Scrapes Arizona DOC Death Row inmate data by emulating ASP.NET postbacks.
# Works fully in GitHub Actions without JavaScript.

import csv
import time
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://inmatedatasearch.azcorrections.gov/DeathRowSearch.aspx"
OUTPUT_CSV = "death_row_inmates.csv"
DELAY_BETWEEN = 1.5  # polite delay

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Helper to extract hidden ASP.NET fields
def get_hidden_fields(soup):
    fields = {}
    for key in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
        tag = soup.find("input", {"name": key})
        fields[key] = tag["value"] if tag and "value" in tag.attrs else ""
    return fields

# Helper to extract inmate detail text
def get_inmate_fields(soup):
    fields = {
        "adc_number": "",
        "name": "",
        "comments": "",
        "proceedings": "",
        "aggravating": "",
        "mitigating": "",
        "pub_opinions": "",
        "mug_image": "",
    }

    def get_text(id_):
        tag = soup.find(id=id_)
        return tag.get_text(strip=True) if tag else ""

    fields["adc_number"] = get_text("lblInmateNumber")
    fields["name"] = get_text("lblName")
    fields["comments"] = get_text("lblComments")
    fields["proceedings"] = get_text("lblProceedings")
    fields["aggravating"] = get_text("lblAggrave")
    fields["mitigating"] = get_text("lblMitigate")
    fields["pub_opinions"] = get_text("lblOpinion")

    img = soup.find("img", {"id": "ImgIMNO_Crime"})
    fields["mug_image"] = img["src"] if img and "src" in img.attrs else ""
    return fields

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Starting scraper:", datetime.utcnow().isoformat() + "Z")

    # Step 1: Load main list page
    resp = session.get(BASE_URL, timeout=60)
    soup = BeautifulSoup(resp.text, "html.parser")

    hidden = get_hidden_fields(soup)
    rows = soup.select("#GVDeathRow tr.GridViewRow, #GVDeathRow tr.GridViewRowAlt")

    # If alternating row styles aren't used, just use all "tr" rows with a link
    if not rows:
        rows = soup.select("#GVDeathRow tr")

    print(f"Found {len(rows)} inmate rows on first page (more pages may exist).")

    inmates = []

    for row in rows:
        link = row.find("a", id=lambda x: x and "CrimeInfo" in x)
        if not link:
            continue
        event_target = link["id"].replace("_", "$")  # ASP.NET expects $ not _
        print(f"Fetching detail for {link.text.strip()} (event target: {event_target})")

        # Prepare POST data for __doPostBack
        post_data = {
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
            **hidden,
        }

        # Step 2: POST back to get inmate details
        detail = session.post(BASE_URL, data=post_data, headers=HEADERS, timeout=60)
        detail_soup = BeautifulSoup(detail.text, "html.parser")

        inmate_data = get_inmate_fields(detail_soup)
        inmate_data["source_url"] = BASE_URL
        inmate_data["scrape_time_utc"] = datetime.utcnow().isoformat() + "Z"
        inmates.append(inmate_data)

        time.sleep(DELAY_BETWEEN)

        # Reload main list for next inmate (resets viewstate)
        resp = session.get(BASE_URL, timeout=60)
        soup = BeautifulSoup(resp.text, "html.parser")
        hidden = get_hidden_fields(soup)

    # Step 3: Write CSV
    fieldnames = [
        "adc_number", "name", "comments", "proceedings", "aggravating",
        "mitigating", "pub_opinions", "mug_image", "source_url", "scrape_time_utc"
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in inmates:
            writer.writerow(row)

    print(f"✅ Done. Scraped {len(inmates)} inmate records.")
    print(f"CSV saved as {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
