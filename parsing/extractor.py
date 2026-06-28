import re
from bs4 import BeautifulSoup


def html_to_text(html):

    soup = BeautifulSoup(html, "html.parser")

    for s in soup(["script", "style"]):
        s.decompose()

    return soup.get_text("\n")


def extract_entity_id(html):

    patterns = [
        r'"publishNoticeId"\s*:\s*(\d+)',
        r'entityId["\']?\s*:\s*["\']?(\d+)',
    ]

    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1)

    return None


def extract_fields(text):

    def find(pattern):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    return {
        "tender_number": find(r"Регистрационный номер\s*(\d+)"),
        "object": find(r"Объект закупки\s*(.+)"),
        "publish_date": find(r"Размещено\s*(\d{2}\.\d{2}\.\d{4})"),
        "end_date": find(r"Окончание\s*(\d{2}\.\d{2}\.\d{4})"),
        "price": find(r"Начальная цена[\s\S]{0,100}?([\d\s,.]+)"),
        "region": find(r"Регион\s*(.+)")
    }