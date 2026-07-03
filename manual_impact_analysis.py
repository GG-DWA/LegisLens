import json

with open("law_profile.json", "r", encoding="utf-8") as f:
    profile = json.load(f)

profile["impact_analysis"] = {
    "actors": [
        "personnes sourdes",
        "personnes malentendantes",
        "personnes sourdaveugles",
        "personnes aphasiques",
        "opérateurs de services téléphoniques",
        "services publics"
    ],
    "sectors": [
        "accessibilité",
        "télécommunications",
        "services publics numériques",
        "inclusion"
    ],
    "main_changes": [
        {
            "title": "Ratification d'une ordonnance relative à l'accessibilité téléphonique",
            "description": "Le texte vise à ratifier l'ordonnance n° 2023-857 concernant l'accessibilité des services téléphoniques pour certains publics en situation de handicap.",
            "source": "Titre du projet de loi"
        }
    ],
    "controversies": [],
    "confidence": "manual_demo"
}

with open("law_profile_analyzed.json", "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=2, ensure_ascii=False)

print(json.dumps(profile, indent=2, ensure_ascii=False))