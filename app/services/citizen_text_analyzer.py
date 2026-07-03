import re
from html import unescape

from app.services.legifrance import consult_best_available_text
from app.services.global_llm_service import build_citizen_answer
from app.services.parliamentary_path_service import build_parliamentary_path
from app.services.real_parliamentary_path_service import build_real_parliamentary_path


def clean_html(raw_html: str | None) -> str:
    if not raw_html:
        return ""

    text = re.sub(r"<br\s*/?>", "\n", raw_html)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)

    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def empty_analysis_response(
    text_id: str,
    origin: str,
    message: str,
    technical_detail: str | None = None,
) -> dict:
    limits = message

    if technical_detail:
        limits = f"{message} Détail technique : {technical_detail}"

    return {
        "query": text_id,
        "text_id": text_id,
        "selected_origin": origin,
        "resolved_origin": None,
        "legi_id": None,
        "jurisState": None,
        "textAbroge": None,
        "answer": {
            "overview": "",
            "actors": [],
            "impacted_sectors": [],
            "law_footprint": [],
            "concrete_changes": [],
            "attention_points": [],
            "official_sources_summary": "",
            "limits": limits,
        },
        "legal_changes": [],
        "source": {
            "id": text_id,
            "cid": None,
            "title": None,
            "nature": None,
            "jorfText": None,
            "jurisState": None,
            "dateDebutVersion": None,
            "dateFinVersion": None,
            "eli": None,
            "alias": None,
        },
        "resolution": {
            "resolved": False,
            "message": message,
        },
        "chunks": [],
        "parliamentary_path": {
            "steps": [],
            "timeline": [],
        },
    }


def extract_legal_changes_from_content(content: str) -> list[dict]:
    changes = []

    patterns = [
        (
            "created",
            r"A créé les dispositions suivantes\s*:\s*-\s*(.+?)(?=\n\n|A modifié|A créé|$)",
        ),
        (
            "modified",
            r"A modifié les dispositions suivantes\s*:\s*-\s*(.+?)(?=\n\n|A modifié|A créé|$)",
        ),
    ]

    for change_type, pattern in patterns:
        matches = re.findall(pattern, content, flags=re.DOTALL)

        for match in matches:
            clean_match = re.sub(r"\s+", " ", match).strip()

            if clean_match:
                changes.append({
                    "type": change_type,
                    "label": "Disposition créée"
                    if change_type == "created"
                    else "Disposition modifiée",
                    "target": clean_match,
                })

    return changes


def extract_legal_changes(data: dict) -> list[dict]:
    legal_changes = []

    for article in data.get("articles", []):
        num = article.get("num", "")
        etat = article.get("etat", "")
        content = clean_html(article.get("content"))

        article_changes = extract_legal_changes_from_content(content)

        for change in article_changes:
            legal_changes.append({
                "article": num,
                "etat": etat,
                **change,
            })

    return legal_changes


def extract_text_content(data: dict) -> str:
    title = data.get("title", "")
    nature = data.get("nature", "")
    jorf_text = data.get("jorfText", "")
    juris_state = data.get("jurisState", "")
    date_debut = data.get("dateDebutVersion", "")
    date_fin = data.get("dateFinVersion", "")
    visa = clean_html(data.get("visa"))
    signers = clean_html(data.get("signers"))

    articles_text = []

    for article in data.get("articles", []):
        num = article.get("num", "")
        etat = article.get("etat", "")
        content = clean_html(article.get("content"))

        if content:
            articles_text.append(
                f"Article {num} — état : {etat}\n{content}"
            )

    return "\n\n".join([
        f"Titre : {title}",
        f"Nature : {nature}",
        f"Publication : {jorf_text}",
        f"État juridique : {juris_state}",
        f"Début de version : {date_debut}",
        f"Fin de version : {date_fin}",
        "Visa :",
        visa,
        "Articles :",
        "\n\n".join(articles_text),
        "Signataires :",
        signers,
    ]).strip()


def split_text_into_chunks(text: str, chunk_size: int = 2500) -> list[str]:
    return [
        text[index:index + chunk_size].strip()
        for index in range(0, len(text), chunk_size)
        if text[index:index + chunk_size].strip()
    ]


def analyze_text_by_id(text_id: str, origin: str) -> dict:
    clean_origin = origin.strip().upper()

    try:
        best_text = consult_best_available_text(
            text_id=text_id,
            origin=clean_origin,
        )
    except Exception as e:
        return empty_analysis_response(
            text_id=text_id,
            origin=clean_origin,
            message="Ce document a été repéré dans la recherche, mais son contenu n'a pas pu être consulté automatiquement pour l'analyse.",
            technical_detail=str(e),
        )

    text_data = best_text.get("legi_text") or best_text.get("jorf_text")

    if not text_data:
        return empty_analysis_response(
            text_id=text_id,
            origin=clean_origin,
            message="Aucun texte exploitable n'a été récupéré pour ce document.",
        )

    try:
        full_text = extract_text_content(text_data)
        chunks = split_text_into_chunks(full_text)
        legal_changes = extract_legal_changes(text_data)
    except Exception as e:
        return empty_analysis_response(
            text_id=text_id,
            origin=clean_origin,
            message="Le texte a été récupéré, mais sa structure n'a pas pu être analysée automatiquement.",
            technical_detail=str(e),
        )

    try:
        parliamentary_path = build_parliamentary_path(text_data)
        real_parliamentary_path = build_real_parliamentary_path(text_data)
    except Exception:
        parliamentary_path = {
            "steps": [],
            "timeline": [],
        }

    if not chunks:
        return empty_analysis_response(
            text_id=text_id,
            origin=clean_origin,
            message="Le texte a été récupéré, mais aucun contenu exploitable n'a été trouvé pour l'analyse.",
        )

    try:
        answer = build_citizen_answer(
            query=text_data.get("title", text_id),
            rag_chunks=chunks,
        )
    except Exception as e:
        return empty_analysis_response(
            text_id=text_id,
            origin=clean_origin,
            message="Le texte officiel a été récupéré, mais l'analyse IA n'a pas pu être générée.",
            technical_detail=str(e),
        )

    return {
        "query": text_data.get("title", text_id),
        "text_id": text_id,
        "selected_origin": best_text.get("selected_origin"),
        "resolved_origin": best_text.get("resolved_origin"),
        "legi_id": best_text.get("legi_id"),
        "jurisState": best_text.get("jurisState"),
        "textAbroge": best_text.get("textAbroge"),
        "answer": answer,
        "legal_changes": legal_changes,
        "source": {
            "title": text_data.get("title"),
            "cid": text_data.get("cid"),
            "id": text_data.get("id"),
            "nature": text_data.get("nature"),
            "jorfText": text_data.get("jorfText"),
            "jurisState": text_data.get("jurisState"),
            "dateDebutVersion": text_data.get("dateDebutVersion"),
            "dateFinVersion": text_data.get("dateFinVersion"),
            "eli": text_data.get("eli"),
            "alias": text_data.get("alias"),
        },
        "resolution": best_text.get("resolution"),
        "chunks": chunks[:5],
        "parliamentary_path": parliamentary_path,
        "real_parliamentary_path": real_parliamentary_path,
    }