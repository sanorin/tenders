import os
from dotenv import load_dotenv
from gigachat import GigaChat

load_dotenv()

GIGACHAT_TOKEN = os.getenv("GIGACHAT_TOKEN")

client = GigaChat(credentials=f"{GIGACHAT_TOKEN}", verify_ssl_certs=False)

PROMPT = """
Ты — система извлечения данных из тендерных документов.

Верни СТРОГО JSON.
Без текста. Без пояснений. Без комментариев.

Если данных нет — используй null или [].

ИЗВЛЕКАЙ:
- оборудование (названия товаров)
- характеристики (если есть)
- контакты (email, телефон, адрес, организация)

ИГНОРИРУЙ:
- законы
- общие условия
- юридический текст

Формат:

{
  "items": [
    {
      "equipment_name": "",
      "equipment_type": "",
      "manufacturer": null,
      "model": null,
      "key_specs": {}
    }
  ],
  "contacts": {
    "organization": "",
    "contact_person": "",
    "email": "",
    "phone": "",
    "address": ""
  }
}

ТЕКСТ:
"""

def extract_data_from_chunk(chunk):
    response = client.chat(PROMPT + chunk)
    return response.choices[0].message.content
