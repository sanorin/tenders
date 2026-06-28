import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from search.search import search_tenders
from download.downloader import download_page
from parsing.extractor import html_to_text
from ai.gigachat import GigaChatClient
from ai.json_utils import safe_json_load


OUTPUT_FILE = "output/tenders.json"
PROCESSED_FILE = "output/processed.json"


def create_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ru-RU"
    })
    return s


def load_processed():
    """Загружает кеш обработанных тендеров {номер: данные}"""
    if not os.path.exists(PROCESSED_FILE):
        return {}
    try:
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_processed(processed):
    os.makedirs("output", exist_ok=True)
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)


def run_pipeline(config, api_key):
    print("\n🚀 PIPELINE START\n")

    session = create_session()
    giga = GigaChatClient(api_key)

    # Кеш всех когда-либо обработанных тендеров
    processed = load_processed()
    # Результаты только текущего запуска
    tenders_map = {}

    urls = search_tenders(session, config)
    print("\nFOUND:", len(urls))

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {
            ex.submit(download_page, url, session): url
            for url in urls
        }

        for f in as_completed(futures):
            source_url = futures[f]

            try:
                reg, path = f.result()
            except Exception as e:
                print("download error:", e)
                continue

            if not path or not reg:
                continue

            # Если тендер уже есть в кеше – берём оттуда и не тратим токены
            if reg in processed:
                print("📦 берём из кеша:", reg)
                tenders_map[reg] = processed[reg]
                continue

            # Новый тендер – обрабатываем
            try:
                with open(path, "r", encoding="utf-8") as file:
                    html = file.read()

                text = html_to_text(html)

                # Предварительная фильтрация по тексту HTML
                exclude_words = config.get("exclude_words", [])
                if exclude_words:
                    text_lower = text.lower()
                    if any(excl.lower() in text_lower for excl in exclude_words):
                        print(f"Исключён по тексту HTML (до GigaChat): {reg}")
                        # Помечаем как обработанный (чтобы не пытаться снова)
                        processed[reg] = None
                        save_processed(processed)
                        continue

                # Вызов GigaChat
                raw = giga.extract(text)
                ai_result = safe_json_load(raw)

                if not ai_result:
                    print("❌ JSON parse error:", reg)
                    processed[reg] = None
                    save_processed(processed)
                    continue

                # Дополняем результат
                ai_result["reg_number"] = reg
                ai_result["url_card"] = source_url
                ai_result["url_source"] = source_url

                # Фильтрация по полю object
                object_text = ai_result.get("object", "").lower()
                skip = False
                for excl in exclude_words:
                    if excl.lower() in object_text:
                        print(f"⛔ Исключён по слову '{excl}' в object: {object_text[:80]}")
                        skip = True
                        break

                if skip:
                    processed[reg] = None
                    save_processed(processed)
                    continue

                # Успешная обработка
                processed[reg] = ai_result
                tenders_map[reg] = ai_result
                save_processed(processed)
                print("🤖 OK:", reg)

            except Exception as e:
                print("processing error:", reg, e)
                continue

    # Сохраняем результаты текущего запуска (перезапись)
    os.makedirs("output", exist_ok=True)
    final_results = list(tenders_map.values())
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)

    print("\n===================")
    print("DONE:", len(final_results))
    print("===================\n")

    return final_results