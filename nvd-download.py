import requests
from time import sleep

for year in range(2002,2027):
    url = f"https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{year}.json.zip"

    r = requests.get(url)

    with open(f"nvdcve-{year}.json.gz", "wb") as f:
        f.write(r.content)

    print("Feed downloaded")
    sleep(2)

