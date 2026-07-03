import json

with open("dossier_detail.json", "r", encoding="utf-8") as f:
    data = json.load(f)

dossier = data["dossierLegislatif"]

print("Titre :")
print(dossier["titre"])

print("\nType :")
print(dossier["type"])

print("\nLiens utiles :")

def extract_links(node):
    for lien in node.get("liens", []):
        print(f"- {lien.get('libelle')}: {lien.get('lien')}")
    for niveau in node.get("niveaux", []):
        extract_links(niveau)

extract_links(dossier["arborescence"])