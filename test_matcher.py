import json
import re
import os
from typing import List, Dict, Any

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ Установите scikit-learn: pip install scikit-learn")

class EquipmentMatcher:
    def __init__(self, equipment_file: str = "equipment.json"):
        self.equipment_file = equipment_file
        self.items = []          # список товаров
        self.texts = []          # текстовые представления для TF-IDF
        self.vectorizer = None
        self.matrix = None

    def load_items(self):
        """Загружает товары из equipment.json и формирует тексты для индексации."""
        if not os.path.exists(self.equipment_file):
            print(f"Файл {self.equipment_file} не найден!")
            return
        with open(self.equipment_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.items = data
        self.texts = []
        for item in self.items:
            # собираем все релевантные поля
            parts = []
            if item.get("product_name"):
                parts.append(item["product_name"])
            if item.get("category"):
                parts.append(item["category"])
            if item.get("lab_type"):
                parts.append(item["lab_type"])
            if item.get("description"):
                # берём только первые 2000 символов описания, чтобы не перегружать
                parts.append(item["description"][:2000])
            text = " ".join(parts).lower()
            self.texts.append(text)
        print(f"Загружено {len(self.items)} товаров.")

    def build_index(self):
        """Строит TF-IDF матрицу."""
        if not SKLEARN_AVAILABLE:
            return
        if not self.texts:
            self.load_items()
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            lowercase=True,
            max_df=0.8,
            min_df=1
        )
        self.matrix = self.vectorizer.fit_transform(self.texts)
        print("TF-IDF матрица построена.")

    def preprocess_query(self, query: str) -> str:
        query = re.sub(r'[^\w\s]', ' ', query)
        return query.lower().strip()

    def match(self, query: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """Возвращает топ-N товаров, отсортированных по релевантности."""
        if not self.texts:
            self.load_items()
        if self.matrix is None and SKLEARN_AVAILABLE:
            self.build_index()

        query_clean = self.preprocess_query(query)

        if not SKLEARN_AVAILABLE:
            # упрощённый режим: поиск по вхождению слов
            words = set(query_clean.split())
            scores = []
            for i, text in enumerate(self.texts):
                matches = sum(1 for w in words if w in text)
                if matches == 0:
                    continue
                score = matches / len(words)
                scores.append((score, i))
            scores.sort(reverse=True, key=lambda x: x[0])
            results = []
            for score, idx in scores[:top_n]:
                item = self.items[idx]
                results.append({
                    "id": item.get("id"),
                    "product_name": item.get("product_name"),
                    "company_name": item.get("company_name"),
                    "score": round(score, 4),
                    "description": item.get("description", "")[:200]
                })
            return results

        # полноценный TF-IDF
        query_vec = self.vectorizer.transform([query_clean])
        similarities = cosine_similarity(query_vec, self.matrix).flatten()
        scored = []
        for idx, sim in enumerate(similarities):
            if sim > 0:
                item = self.items[idx]
                scored.append({
                    "id": item.get("id"),
                    "product_name": item.get("product_name"),
                    "company_name": item.get("company_name"),
                    "score": round(float(sim), 4),
                    "description": item.get("description", "")[:200]
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

if __name__ == "__main__":
    matcher = EquipmentMatcher()
    q = input("🔍 Введите описание оборудования: ")
    results = matcher.match(q, top_n=10)
    print(f"\nНайдено {len(results)} релевантных товаров:\n")
    for i, res in enumerate(results, 1):
        print(f"{i}. {res['product_name']} — релевантность: {res['score']*100:.1f}%")
        print(f"   Производитель: {res['company_name']}")
        print(f"   Описание: {res['description']}...")
        print()