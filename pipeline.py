import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import time

from pdf_parser.extractor import extract_text
from processing.chunking import split_text
from processing.llm import extract_data_from_chunk
from processing.json_utils import safe_json_load
from processing.deduplication import deduplicate
from processing.text_cleaning import clean_text


# настройки
BASE_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"

KEYWORDS = ["робот", "робототехника", "РОББО"]
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

DAYS_TO_KEEP = 7


def get_date_range(days=DAYS_TO_KEEP):
    today = datetime.now()
    start_date = today - timedelta(days=days)
    return start_date.strftime("%d.%m.%Y"), today.strftime("%d.%m.%Y")

def clean_old_files(folder, days=DAYS_TO_KEEP, valid_files=None):
    now = datetime.now()
    if not os.path.exists(folder):
        os.makedirs(folder)
        return
    
    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if not os.path.isfile(path):
            continue
        file_time = datetime.fromtimestamp(os.path.getmtime(path))
        file_name_without_ext = os.path.splitext(file)[0]
        
        # Удаляем если файл старше days дней ИЛИ файл не в списке актуальных
        if (now - file_time > timedelta(days=days) or 
            (valid_files is not None and file_name_without_ext not in valid_files)):
            os.remove(path)
            reason = "старый" if now - file_time > timedelta(days=days) else "неактуальный"
            print(f"Удалён файл: {file} (причина: {reason})")

@lru_cache(maxsize=1000)
def extract_reg_number_cached(url):
    """Кэшированная версия extract_reg_number"""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("regNumber", [None])[0]

def filter_single_tender(url, session):
    """Фильтрация одного тендера"""
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()
        
        # Быстрая проверка ключевых слов
        if not any(k.lower() in text for k in KEYWORDS):
            return None
        
        # Проверка исключений
        if any(w in text for w in EXCLUDE_WORDS):
            return None
        
        # Проверка региона
        if "санкт-петербург" not in text and "г. санкт-петербург" not in text:
            return None
        
        return url
        
    except requests.RequestException as e:
        print(f"Ошибка при фильтрации {url}: {e}")
        return None

def get_tenders_optimized(days=DAYS_TO_KEEP, max_workers=10):
    """Оптимизированная версия с параллельными запросами и кэшированием"""
    date_from, date_to = get_date_range(days)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    session = requests.Session()
    session.headers.update(headers)
    
    # Собираем URL тендеров для всех ключевых слов
    all_tender_urls = set()
    
    print("Сбор ссылок на тендеры...")
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
            
            try:
                response = session.get(BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                
                tenders_on_page = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "common-info.html" in href:
                        full_url = "https://zakupki.gov.ru" + href
                        tenders_on_page.append(full_url)
                
                if not tenders_on_page:
                    break
                    
                all_tender_urls.update(tenders_on_page)
                page += 1
                
            except requests.RequestException as e:
                print(f"Ошибка при загрузке страницы {page} для ключевого слова {keyword}: {e}")
                break
    
    print(f"Найдено уникальных тендеров: {len(all_tender_urls)}")
    
    # Параллельная фильтрация тендеров
    print("Фильтрация тендеров...")
    filtered_tenders = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(filter_single_tender, url, session): url 
            for url in all_tender_urls
        }
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result(timeout=15)
                if result:
                    filtered_tenders.append(result)
            except Exception as e:
                print(f"Ошибка при обработке {url}: {e}")
    
    return filtered_tenders

def download_print_form_optimized(reg_number, folder=None, session=None):
    """Скачивание с переиспользованием сессии"""
    if folder is None:
        folder = INPUT_FOLDER
    
    if session is None:
        session = requests.Session()
    
    url = f"https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber={reg_number}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        file_name = f"{reg_number}.html"
        path = os.path.join(folder, file_name)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        print(f"✅ Сохранён HTML: {file_name}")
        return path
        
    except requests.RequestException as e:
        print(f"Ошибка скачивания {reg_number}: {e}")
        return None

def process_file(file_path):
    text = extract_text(file_path)
    text = clean_text(text)
    chunks = split_text(text)
    all_items = []
    contacts = None

    for chunk in chunks:
        raw_json = extract_data_from_chunk(chunk)
        data = safe_json_load(raw_json)
        if not data:
            continue
        if "items" in data:
            all_items.extend(data["items"])
        if not contacts and "contacts" in data:
            contacts = data["contacts"]

    all_items = deduplicate(all_items)
    return {"items": all_items, "contacts": contacts}

def run_pipeline_optimized(days=DAYS_TO_KEEP):
    print(f"Запуск пайплайна: ищем за последние {days} дней...")
    start_time = time.time()
    tenders = get_tenders_optimized(days=days, max_workers=10)
    elapsed = time.time() - start_time
    print(f"Найдено тендеров: {len(tenders)}, время выполнения: {elapsed:.2f} сек")
    
    # Собираем номера актуальных тендеров
    reg_numbers = [extract_reg_number_cached(tender) for tender in tenders if extract_reg_number_cached(tender)]
    valid_files = set(reg_numbers)  # Используем set для быстрого поиска
    
    # Очистка старых файлов с передачей списка актуальных
    print("Очистка старых файлов...")
    clean_old_files(INPUT_FOLDER, days, valid_files)
    clean_old_files(OUTPUT_FOLDER, days, valid_files)
    
    # Если нет актуальных тендеров, завершаем работу
    if len(tenders) == 0:
        print("Нет актуальных тендеров для обработки. Все неактуальные файлы удалены.")
        return
    
    # скачивание
    print("Скачивание тендеров...")
    downloaded_files = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_reg = {
            executor.submit(download_print_form_optimized, reg_number, INPUT_FOLDER): reg_number
            for reg_number in reg_numbers if reg_number
        }
        
        for future in as_completed(future_to_reg):
            reg_number = future_to_reg[future]
            try:
                path = future.result(timeout=20)
                if path:
                    downloaded_files.append(os.path.splitext(os.path.basename(path))[0])
            except Exception as e:
                print(f"Ошибка при скачивании {reg_number}: {e}")
    
    # Обработка файлов
    print("Обработка файлов...")
    for file_name in os.listdir(INPUT_FOLDER):
        if not file_name.endswith(".html"):
            continue
            
        file_path = os.path.join(INPUT_FOLDER, file_name)
        base_name = os.path.splitext(file_name)[0]
        output_file = os.path.join(OUTPUT_FOLDER, base_name + ".json")
        
        # Пропускаем файлы, которые не входят в список актуальных
        if base_name not in valid_files:
            continue
            
        if os.path.exists(output_file):
            print(f"Уже обработан: {file_name}")
            continue
            
        result = process_file(file_path)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Создан JSON: {output_file}")

if __name__ == "__main__":
    run_pipeline_optimized()