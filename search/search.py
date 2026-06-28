import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

BASE_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"


def get_date_range(days):

    now = datetime.now()
    start = now - timedelta(days=days)

    return start.strftime("%d.%m.%Y"), now.strftime("%d.%m.%Y")


def search_tenders(session, config):

    start, end = get_date_range(config["days"])

    urls = set()

    exclude_words = config.get("exclude_words", [])

    for kw in config["keywords"]:

        page = 1
        MAX_PAGES = 10
        seen = set()

        while page <= MAX_PAGES:

            params = {
                "searchString": kw,
                "pageNumber": page,
                "recordsPerPage": "_50",
                "publishDateFrom": start,
                "publishDateTo": end,
                "morphology": "on",
            }

            r = session.get(BASE_URL, params=params, timeout=20)

            html = r.text
            fingerprint = hash(html[:8000])

            if fingerprint in seen:
                break

            seen.add(fingerprint)

            soup = BeautifulSoup(html, "html.parser")

            links = []

            for a in soup.find_all("a", href=True):
                if "common-info.html" in a["href"]:

                    link_text = a.get_text().strip().lower()

                    parent = a.find_parent()
                    if parent and not link_text:
                        link_text = parent.get_text().strip().lower()

                    skip = False
                    for ex in exclude_words:
                        if ex.lower() in link_text:
                            print(f"⛔ Пропускаем по слову '{ex}': {link_text[:80]}")
                            skip = True
                            break
                    if skip:
                        continue

                    original_url = a["href"]
                    parsed_url = urlparse(original_url)
                    params = parse_qs(parsed_url.query)

                    # Извлекаем номер закупки (обычно параметр regNumber)
                    reg_number = params.get("regNumber", [None])[0]

                    if reg_number:
                        # Проверяем, это 223-ФЗ или 44-ФЗ (по пути в ссылке)
                        if "notice223" in original_url:
                            # Шаблон для 223-ФЗ
                            print_url = f"https://zakupki.gov.ru/epz/order/notice/notice223-new/printForm/view.html?purchaseNoticeNumber={reg_number}"
                        else:
                            # Шаблон для 44-ФЗ
                            print_url = f"https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber={reg_number}"

                        urls.add(print_url)

            if not links:
                break

            urls.update(links)

            print(f"{kw} page {page} | {len(links)}")

            page += 1

    return list(urls)