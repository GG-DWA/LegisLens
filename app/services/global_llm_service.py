from groq import Groq
from dotenv import load_dotenv

import json
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def clean_json_response(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]

    if content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def build_citizen_answer(query: str, rag_chunks: list[str]) -> dict:
    context = "\n\n".join(rag_chunks[:8])

    prompt = f"""
Tu es un assistant d'analyse législative citoyenne.

Question :
{query}

Documents officiels :
{context}

Tu dois répondre UNIQUEMENT en JSON valide.
Ne mets jamais de Markdown.

Structure EXACTE :

{{
    "overview": "",

    "actors": [
        {{
            "name": "",
            "reason": ""
        }}
    ],

    "impacted_sectors": [
        {{
            "name": "",
            "reason": ""
        }}
    ],

    "law_footprint": [
        {{
            "target": "",
            "impact": ""
        }}
    ],

    "concrete_changes": [
        {{
            "title": "",
            "description": ""
        }}
    ],

    "attention_points": [
        {{
            "title": "",
            "description": ""
        }}
    ],

    "official_sources_summary": "",

    "limits": ""
}}

Contraintes :

- Réponds en français clair, compréhensible par un citoyen.
- Utilise uniquement les informations présentes dans les documents.
- N'invente jamais d'information.
- Ne donne pas de conseil juridique.
- Si une information n'existe pas dans les documents, retourne une liste vide.

La section "overview" doit :
- expliquer en quelques phrases l'objectif principal de la loi ;
- terminer par une phrase simple résumant son objectif concret pour le citoyen.

La section "actors" doit :
- identifier uniquement les acteurs directement concernés ;
- privilégier : citoyens, entreprises, administrations, collectivités, associations, professionnels, services publics ;
- ne pas citer des ministères sauf s'ils jouent un rôle essentiel dans l'application de la loi.

La section "impacted_sectors" correspond aux secteurs ou domaines impactés par la loi.
Ne retourne jamais un ministère comme secteur.
Privilégie des secteurs tels que :
- Numérique
- Télécommunications
- Santé
- Education
- Justice
- Handicap
- Inclusion
- Services publics
- Logement
- Environnement
- Agriculture
- Energie
- Transports
- Fiscalité

La section "law_footprint" représente l'empreinte concrète de la loi.
Elle doit expliquer les conséquences de la loi sur les différentes catégories concernées.
Privilégie notamment :
- Citoyens
- Entreprises
- Administrations
- Collectivités
- Services publics
- Société

Chaque impact doit être formulé en une ou deux phrases simples.

La section "concrete_changes" doit présenter uniquement les changements réellement introduits par la loi.

La section "attention_points" doit signaler uniquement les éléments nécessitant une vigilance particulière.

La section "official_sources_summary" doit résumer en une phrase quels documents officiels ont servi à produire l'analyse.

La section "limits" doit expliquer les limites des documents disponibles lorsque certaines informations ne sont pas présentes.
"""

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
        return json.loads(
            clean_json_response(content)
        )

    except Exception:
        return {
            "overview": "",
            "actors": [],
            "impacted_sectors": [],
            "law_footprint": [],
            "concrete_changes": [],
            "attention_points": [],
            "official_sources_summary": "",
            "limits": "Impossible d'interpréter correctement la réponse du modèle.",
            "raw_response": content,
        }