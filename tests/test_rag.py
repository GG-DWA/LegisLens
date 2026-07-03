import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.rag_service import (
    build_rag_index,
    search_rag
)

text = """
La loi prévoit une solution d’accessibilité
téléphonique universelle pour les personnes
sourdes, malentendantes, sourdaveugles et aphasiques.

Les entreprises doivent respecter leurs
obligations d’accessibilité.

Un régime de sanction administrative est créé.
"""

store = build_rag_index(text)

results = search_rag(
    store,
    "accessibilité"
)

for r in results:
    print()
    print("=" * 50)
    print(r)