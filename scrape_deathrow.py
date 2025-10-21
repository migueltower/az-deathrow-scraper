import requests
from bs4 import BeautifulSoup

url = "https://inmatedatasearch.azcorrections.gov/DeathRowSearch.aspx"
print("Fetching:", url)

r = requests.get(url, timeout=60)
print("HTTP status:", r.status_code)

# Save the raw HTML so we can see what GitHub actually got
with open("page_snapshot.html", "w", encoding="utf-8") as f:
    f.write(r.text)

# Quick summary
soup = BeautifulSoup(r.text, "html.parser")
table = soup.find("table", {"id": "GVDeathRow"})
if table:
    print("✅ Found inmate table GVDeathRow.")
    print("First 300 chars:")
    print(table.get_text(strip=True)[:300])
else:
    print("⚠️ No GVDeathRow table found in HTML.")
