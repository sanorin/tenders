from bs4 import BeautifulSoup
import pdfplumber


def extract_text(file_path):
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    elif file_path.endswith(".html"):
        return extract_text_from_html(file_path)


def extract_text_from_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    return soup.get_text(separator=" ")
