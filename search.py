import os
import json

OUTPUT_FOLDER = "output"

def search_in_json(obj, query_words):
    """Рекурсивно ищем ключевые слова в любом месте JSON"""
    if isinstance(obj, dict):
        return any(search_in_json(v, query_words) for v in obj.values())
    elif isinstance(obj, list):
        return any(search_in_json(item, query_words) for item in obj)
    elif isinstance(obj, str):
        text = obj.lower()
        return any(w in text for w in query_words)
    return False

def search_database(query):
    query_words = [w.lower() for w in query.split()]
    results = []

    for file_name in os.listdir(OUTPUT_FOLDER):
        if not file_name.endswith(".json"):
            continue
        path = os.path.join(OUTPUT_FOLDER, file_name)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if search_in_json(data, query_words):
            results.append({"file": file_name, "data": data})

    return results

if __name__ == "__main__":
    query = input("🔍 Введите запрос для поиска: ")
    search_results = search_database(query)
    print(f"\nНайдено {len(search_results)} подходящих тендеров:\n")
    for r in search_results[:10]:
        print(f"{r['file']}")
        # Опционально: показать первые 5 items
        for item in r["data"].get("items", [])[:5]:
            print("  •", item.get("name"), "-", item.get("description", "")[:50], "...")
        print()

if __name__ == "__main__":
    query = input("🔍 Введите запрос для поиска: ")
    search_results = search_database(query)

    print(f"\nНайдено {len(search_results)} подходящих тендеров:\n")

    for idx, r in enumerate(search_results[:10], 1):
        print(f"{idx}. {r['file']}")
        for item in r["data"].get("items", [])[:5]:
            print("  •", item.get("name"), "-", str(item.get("description", ""))[:50], "...")
