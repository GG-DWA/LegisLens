from pathlib import Path
import requests
import fitz


PDF_DIR = Path("data/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)


def download_pdf(url: str, filename: str) -> Path:
    output_path = PDF_DIR / filename

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(output_path, "wb") as file:
        file.write(response.content)

    return output_path


def extract_text_from_pdf(pdf_path: Path) -> str:
    document = fitz.open(pdf_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


def download_and_extract_pdf(url: str, filename: str) -> str:
    pdf_path = download_pdf(url, filename)
    return extract_text_from_pdf(pdf_path)