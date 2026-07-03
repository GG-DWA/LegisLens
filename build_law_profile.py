import json

with open("dossier_detail.json", "r", encoding="utf-8") as f:
    data = json.load(f)

dossier = data["dossierLegislatif"]

links = []

def extract_links(node):
    for lien in node.get("liens", []):
        links.append({
            "label": lien.get("libelle"),
            "url": lien.get("lien"),
            "data": lien.get("data")
        })
    for niveau in node.get("niveaux", []):
        extract_links(niveau)

extract_links(dossier["arborescence"])

profile = {
    "id": dossier["id"],
    "title": dossier["titre"],
    "type": dossier["type"],
    "legislature": dossier["legislature"]["libelle"],
    "sources": links,
    "impact_analysis": {
        "actors": [],
        "sectors": [],
        "main_changes": [],
        "controversies": [],
        "confidence": "not_analyzed_yet"
    }
}

with open("law_profile.json", "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=2, ensure_ascii=False)

print(json.dumps(profile, indent=2, ensure_ascii=False))