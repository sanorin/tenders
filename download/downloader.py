import os
from urllib.parse import urlparse, parse_qs


INPUT_FOLDER = "input"
os.makedirs(INPUT_FOLDER, exist_ok=True)


def extract_reg_number(url):
    try:
        return parse_qs(urlparse(url).query).get("regNumber", [None])[0]
    except:
        return None


def download_page(url, session):

    reg = extract_reg_number(url)

    if not reg:
        return None, None

    try:

        r = session.get(url, timeout=20)

        if r.status_code != 200:
            return None, None

        path = os.path.join(INPUT_FOLDER, f"{reg}.html")

        with open(path, "w", encoding="utf-8") as f:
            f.write(r.text)

        print("📥 saved", reg)

        return reg, path

    except:
        return None, None