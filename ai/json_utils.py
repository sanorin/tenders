import json
import re


def safe_json_load(raw: str):
    if not raw:
        return None

    raw = raw.strip()

    # =========================
    # 1. убираем ```json ```
    # =========================
    raw = re.sub(r"```json|```", "", raw).strip()

    # =========================
    # 2. вырезаем первый JSON объект
    # =========================
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None

    raw = match.group(0)

    # =========================
    # 3. убираем trailing commas (ВАЖНО)
    # =========================
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)

    # =========================
    # 4. парсим
    # =========================
    try:
        return json.loads(raw)
    except Exception as e:
        print("JSON FIX FAILED:", e)
        print("RAW:", raw)
        return None