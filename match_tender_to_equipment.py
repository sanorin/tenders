import json
from equipment_matcher import EquipmentMatcher

# 1. Загружаем тендер
tender_file = "output/0372200284426000019.json"
with open(tender_file, "r", encoding="utf-8") as f:
    tender = json.load(f)

items = tender.get("items", [])
print(f"Тендер содержит {len(items)} позиций:\n")

# 2. Инициализируем матчер по базе оборудования
matcher = EquipmentMatcher()
matcher.load_items()
matcher.build_index()

# 3. Для каждого товара ищем в базе
for idx, item in enumerate(items, 1):
    name = item.get("equipment_name", "Без названия")
    print(f"{idx}. Товар из тендера: \"{name}\"")
    results = matcher.match(name, top_n=1)  # берём лучшее совпадение
    if results:
        best = results[0]
        print(f"   → Совпадает с: \"{best['product_name']}\" (компания: {best['company_name']}, релевантность: {best['score']*100:.1f}%)")
    else:
        print("   → Совпадений не найдено.")
    print()