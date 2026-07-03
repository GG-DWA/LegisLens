import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.document_loader import download_and_extract_pdf
from app.services.rag_service import build_rag_index, search_rag


url = "https://www.legifrance.gouv.fr/contenu/Media/files/autour-de-la-loi/legislatif-et-reglementaire/actualite-legislative/2024/pjl_tssp2407983l_cm_10.04.2024.pdf"

text = download_and_extract_pdf(
    url,
    "rag_test_fin_de_vie.pdf"
)

store = build_rag_index(text)

results = search_rag(
    store,
    "soins d'accompagnement et droits des malades"
)

for result in results:
    print()
    print("=" * 80)
    print(result[:1200])