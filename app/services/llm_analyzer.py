from groq import Groq
from dotenv import load_dotenv
from app.services.document_loader import download_and_extract_pdf

import os
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def clean_json_response(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content.replace("```json", "", 1)

    if content.startswith("```"):
        content = content.replace("```", "", 1)

    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def get_pdf_content(sources: list[dict]) -> str:
    content = ""

    target_labels = [
        "Projet de loi",
        "Exposé des motifs",
        "Etude d'impact",
    ]

    for source in sources:
        label = source.get("label", "")
        url = source.get("url", "")

        if label in target_labels and url.endswith(".pdf"):
            try:
                filename = (
                    label.lower()
                    .replace(" ", "_")
                    .replace("'", "")
                    .replace("é", "e")
                    .replace("è", "e")
                    .replace("ê", "e")
                    + ".pdf"
                )

                text = download_and_extract_pdf(url, filename)

                content += (
                    f"\n\n===== {label} =====\n\n"
                    + text[:4000]
                )

            except Exception as e:
                print(f"Erreur PDF {label}: {e}")

    return content[:12000]


def build_prompt(dossier_data: dict, sources: list[dict]) -> str:
    title = dossier_data.get("titre", "")
    source_labels = [source.get("label") for source in sources[:12]]
    pdf_content = get_pdf_content(sources)

    return f"""
Tu es un assistant d'analyse législative.

Analyse le dossier législatif suivant uniquement à partir des informations fournies.

Titre :
{title}

Sources disponibles :
{source_labels}

Extraits de documents officiels :
{pdf_content}

Objectif :
Produire une fiche d'empreinte de la loi.

Identifie :
- les acteurs concernés ;
- les secteurs concernés ;
- les droits concernés ;
- les procédures concernées ;
- les articles de loi modifiés ;
- les structures concernées ;
- les nouveaux dispositifs créés ;
- les principaux changements.

Pour chaque élément identifié :
- indique le document source utilisé ;
- indique un court extrait exact ou quasi exact du document ;
- limite l'extrait à 300 caractères maximum ;
- n'invente jamais une citation ;
- si aucun extrait n'est disponible, laisse source_document et source_excerpt vides.

Contraintes :
- Ne donne jamais de score d'impact.
- Ne classe pas l'impact en fort, moyen ou faible.
- N'invente pas d'information absente du titre, des sources ou des extraits fournis.
- Si une information n'est pas suffisamment appuyée par les documents, laisse le champ vide.
- Réponds uniquement en JSON valide.
- Ne mets pas de bloc Markdown.
- Ne mets pas ```json.

Structure JSON obligatoire :

{{
  "summary": "",

  "actors": [
    {{
      "name": "",
      "reason": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ],

  "sectors": [
    {{
      "name": "",
      "reason": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ],

  "rights_impacted": [
    {{
      "name": "",
      "reason": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ],

  "procedures_impacted": [
    {{
      "name": "",
      "reason": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ],

  "articles_impacted": [
    {{
      "article": "",
      "change": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ],

  "structures_concerned": [
    {{
      "name": "",
      "reason": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ],

  "new_measures": [
    {{
      "name": "",
      "description": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ],

  "main_changes": [
    {{
      "title": "",
      "description": "",
      "source_document": "",
      "source_excerpt": ""
    }}
  ]
}}
"""


def analyze_with_llm(dossier_data: dict, sources: list[dict]) -> dict:
    title = dossier_data.get("titre", "")
    prompt = build_prompt(dossier_data, sources)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    content = response.choices[0].message.content

    try:
        cleaned_content = clean_json_response(content)
        analysis = json.loads(cleaned_content)

    except json.JSONDecodeError:
        analysis = {
            "summary": "La réponse IA n'a pas pu être convertie en JSON.",
            "actors": [],
            "sectors": [],
            "rights_impacted": [],
            "procedures_impacted": [],
            "articles_impacted": [],
            "structures_concerned": [],
            "new_measures": [],
            "main_changes": [],
            "raw_response": content,
        }

    analysis["title"] = title
    analysis["sources"] = sources
    analysis["confidence"] = "llm_generated_with_pdf_extracts_and_sources"

    return analysis