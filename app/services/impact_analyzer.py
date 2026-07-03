from app.services.llm_analyzer import analyze_with_llm


def extract_sources(node: dict) -> list[dict]:
    sources = []

    for link in node.get("liens", []):
        sources.append({
            "label": link.get("libelle"),
            "url": link.get("lien"),
            "data": link.get("data")
        })

    for child in node.get("niveaux", []):
        sources.extend(extract_sources(child))

    return sources


def analyze_dossier(dossier: dict) -> dict:
    dossier_data = dossier.get("dossierLegislatif", {})
    sources = extract_sources(dossier_data.get("arborescence", {}))

    return analyze_with_llm(dossier_data, sources)