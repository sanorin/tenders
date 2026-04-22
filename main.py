import os
import json
from pdf_parser.extractor import extract_text
from processing.chunking import split_text
from processing.llm import extract_data_from_chunk
from processing.json_utils import safe_json_load
from processing.deduplication import deduplicate
from processing.text_cleaning import clean_text
from datetime import datetime, timedelta

def process_pdf(file_path):
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


def clean_old_json(input_folder="input", output_folder="output", days=7):
    now = datetime.now()
    input_files = {os.path.splitext(f)[0] for f in os.listdir(input_folder) if f.endswith(".html") or f.endswith(".pdf")}

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file in os.listdir(output_folder):
        if not file.endswith(".json"):
            continue
        base_name = os.path.splitext(file)[0]
        path = os.path.join(output_folder, file)
        file_time = datetime.fromtimestamp(os.path.getmtime(path))
        if now - file_time > timedelta(days=days) or base_name not in input_files:
            os.remove(path)
            print("Удалён старый JSON:", file)

def main():
    input_folder = "input"
    output_folder = "output"

    clean_old_json(input_folder, output_folder)  # очистка старых JSON

    for file_name in os.listdir(input_folder):
        if not (file_name.endswith(".pdf") or file_name.endswith(".html")):
            continue

        file_path = os.path.join(input_folder, file_name)
        base_name = os.path.splitext(file_name)[0]
        output_file = os.path.join(output_folder, base_name + ".json")

        if os.path.exists(output_file):
            print("Уже обработан:", file_name)
            continue

        result = process_pdf(file_path)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Готово: {output_file}")

if __name__ == "__main__":
    main()
