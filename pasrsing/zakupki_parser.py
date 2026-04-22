import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs


BASE_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"

INPUT_FOLDER = "input"


# ключевые слова
KEYWORDS = [
    "робот",
    "робототехника",
    "РОББО"
]

# исключения
EXCLUDE_WORDS = [
    "уборщик", "хирургической", "обзвону", "газонокосилки",
    "мусоросборщика", "противопожарной", "экскурсовода",
    "дозирования", "пылесоса", "медицинских",
    "мойщик", "автомобилей", "очиститель",
    "овощерезка", "поломоечной", "дезинфекционных",
    "орторент", "сустав", "голосового",
    "fanuc", "kuka", "книг", "тренажёра",
    "пипетки", "демонтажных", "лизинг",
    "роботизированного", "мероприятий",
    "ложемент", "доярки", "питания"
]




def get_date_range(days=7):
    today = datetime.now()
    start_date = today - timedelta(days=days)
    return start_date.strftime("%d.%m.%Y"), today.strftime("%d.%m.%Y")




def clean_old_files(folder=INPUT_FOLDER, days=7):
    now = datetime.now()

    if not os.path.exists(folder):
        os.makedirs(folder)

    for file in os.listdir(folder):
        path = os.path.join(folder, file)

        if not os.path.isfile(path):
            continue

        file_time = datetime.fromtimestamp(os.path.getmtime(path))

        if now - file_time > timedelta(days=days):
            os.remove(path)
            print("Удалён старый файл:", file)


# поиск тендеров
def get_tenders():
    date_from, date_to = get_date_range(7)
    all_tenders = []

    headers = {"User-Agent": "Mozilla/5.0"}

    for keyword in KEYWORDS:
        page = 1
        while True:
            params = {
                "searchString": keyword,
                "morphology": "on",
                "pageNumber": page,
                "recordsPerPage": "_50",
                "publishDateFrom": date_from,
                "publishDateTo": date_to,
                "fz44": "on",
                "regionId": "78"
            }

            response = requests.get(BASE_URL, params=params, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            tenders_on_page = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "common-info.html" in href:
                    full_url = "https://zakupki.gov.ru" + href
                    tenders_on_page.append(full_url)

            if not tenders_on_page:
                break
            all_tenders.extend(tenders_on_page)
            page += 1

    all_tenders = list(set(all_tenders))
    filtered_tenders = []


    for url in all_tenders:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()


        if "санкт-петербург" not in text and "г. санкт-петербург" not in text:
            continue


        if not any(k.lower() in text for k in KEYWORDS):
            continue

        if any(w in text for w in EXCLUDE_WORDS):
            continue

        filtered_tenders.append(url)

    return filtered_tenders



def extract_reg_number(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("regNumber", [None])[0]


def get_documents_page(reg_number, tender_url):
    if "ea20" in tender_url:
        type_ = "ea20"
    elif "zk20" in tender_url:
        type_ = "zk20"
    elif "ezt20" in tender_url:
        type_ = "ezt20"
    else:
        type_ = "ea20"

    url = f"https://zakupki.gov.ru/epz/order/notice/{type_}/documents.html?regNumber={reg_number}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)

    return response.text


# поиск пдф
def get_pdf_links(reg_number, tender_url):
    html = get_documents_page(reg_number, tender_url)
    soup = BeautifulSoup(html, "html.parser")

    pdf_links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if ".pdf" in href.lower():
            if href.startswith("http"):
                pdf_links.append(href)
            else:
                pdf_links.append("https://zakupki.gov.ru" + href)

    return list(set(pdf_links))


# скачивание
def download_print_form(reg_number, folder=INPUT_FOLDER):
    url = f"https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber={reg_number}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)

    file_name = f"{reg_number}.html"
    path = os.path.join(folder, file_name)

    with open(path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print("✅ Сохранён HTML:", file_name)

    return path



# удаление старых
def clean_old_files(folder=INPUT_FOLDER, days=7):
    now = datetime.now()

    if not os.path.exists(folder):
        os.makedirs(folder)

    for file in os.listdir(folder):
        path = os.path.join(folder, file)

        if not os.path.isfile(path):
            continue

        file_time = datetime.fromtimestamp(os.path.getmtime(path))

        if now - file_time > timedelta(days=days):
            os.remove(path)
            print("Удалён старый файл:", file)




def run():
    clean_old_files()  

    tenders = get_tenders()
    print("Найдено тендеров:", len(tenders))

    for tender in tenders:
        print("\nТендер:", tender)

        reg_number = extract_reg_number(tender)
        if not reg_number:
            continue

        download_print_form(reg_number)

if __name__ == "__main__":
    run()

