import os
from datetime import datetime, timezone
import re

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"


TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0,
}


def get_token() -> str:
    now = int(datetime.now(timezone.utc).timestamp())

    if TOKEN_CACHE["access_token"] and TOKEN_CACHE["expires_at"] > now + 60:
        return TOKEN_CACHE["access_token"]

    client_id = os.getenv("LEGIFRANCE_CLIENT_ID")
    client_secret = os.getenv("LEGIFRANCE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Identifiants PISTE manquants dans .env")

    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": "openid"},
        auth=(client_id, client_secret),
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    TOKEN_CACHE["access_token"] = data["access_token"]
    TOKEN_CACHE["expires_at"] = now + int(data.get("expires_in", 3600))

    return TOKEN_CACHE["access_token"]


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }


def ping_legifrance() -> str:
    response = requests.get(
        f"{BASE_URL}/consult/ping",
        headers=get_headers(),
    )
    response.raise_for_status()
    return response.text


def normalize_bool(value: bool | str) -> bool:
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ["true", "1", "yes", "oui"]


def clean_html_marks(value: str | None) -> str:
    if not value:
        return ""

    return (
        value
        .replace("<mark>", "")
        .replace("</mark>", "")
        .strip()
    )


def get_legi_timestamp() -> int:
    year = datetime.now(timezone.utc).year

    return int(
        datetime(year, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
    )


def get_dossiers(
    legislature_id: int = 16,
    dossier_type: str = "PROJET_LOI",
) -> dict:
    response = requests.post(
        f"{BASE_URL}/list/dossiersLegislatifs",
        headers=get_headers(),
        json={
            "legislatureId": legislature_id,
            "type": dossier_type,
        },
    )

    response.raise_for_status()
    return response.json()


def get_dossier_detail(dossier_id: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/consult/dossierLegislatif",
        headers=get_headers(),
        json={"id": dossier_id},
    )

    response.raise_for_status()
    return response.json()


def get_loda(page_number: int = 1, page_size: int = 5) -> dict:
    response = requests.post(
        f"{BASE_URL}/list/loda",
        headers=get_headers(),
        json={
            "pageNumber": page_number,
            "pageSize": page_size,
        },
    )

    response.raise_for_status()
    return response.json()


def consult_jorf_text(text_cid: str) -> dict:
    clean_text_cid = text_cid.split("_")[0]

    response = requests.post(
        f"{BASE_URL}/consult/jorf",
        headers=get_headers(),
        json={"textCid": clean_text_cid},
    )

    response.raise_for_status()
    return response.json()


def consult_legi_text(text_id: str) -> dict:
    clean_text_id = text_id.split("_")[0]

    response = requests.post(
        f"{BASE_URL}/consult/legiPart",
        headers=get_headers(),
        json={
            "textId": clean_text_id,
            "date": get_legi_timestamp(),
        },
    )

    response.raise_for_status()
    return response.json()


def get_loda_detail(text_id: str) -> dict:
    return consult_legi_text(text_id)


def get_chrono_text_cid(text_cid: str) -> dict:
    clean_text_cid = text_cid.split("_")[0]

    response = requests.post(
        f"{BASE_URL}/chrono/textCid",
        headers=get_headers(),
        json={"textCid": clean_text_cid},
    )

    response.raise_for_status()
    return response.json()


def resolve_jorf_to_legi(text_cid: str) -> dict:
    clean_text_cid = text_cid.split("_")[0]
    chrono_data = get_chrono_text_cid(clean_text_cid)

    for regroupement in chrono_data.get("regroupements", []):
        versions = regroupement.get("versions", {})

        for version_data in versions.values():
            articles_modificateurs = version_data.get(
                "articlesModificateurs",
                {},
            )

            for article_data in articles_modificateurs.values():
                actions = article_data.get("actions", {})
                versement = actions.get("VERSEMENT")

                if not versement:
                    continue

                parents = versement.get("parents", {})

                for legi_id, parent_data in parents.items():
                    if legi_id.startswith("LEGITEXT"):
                        return {
                            "resolved": True,
                            "legi_id": legi_id,
                            "legi": parent_data,
                            "chrono": {
                                "source_text_cid": clean_text_cid,
                                "date_debut": parent_data.get("dateDebut"),
                                "nature": parent_data.get("nature"),
                                "cid": parent_data.get("cid"),
                                "name": parent_data.get("name"),
                            },
                            "message": "Texte LEGI trouvé via /chrono/textCid.",
                        }

    return {
        "resolved": False,
        "legi_id": None,
        "legi": None,
        "chrono": {"source_text_cid": clean_text_cid},
        "message": "Aucun LEGITEXT trouvé via /chrono/textCid.",
    }


def consult_text(text_id: str, origin: str) -> dict:
    clean_origin = origin.strip().upper()

    if clean_origin == "JORF":
        return consult_jorf_text(text_id)

    if clean_origin in ["LEGI", "CODE", "LODA"]:
        return consult_legi_text(text_id)

    return {
        "status_code": 400,
        "message": (
            "Origine non supportée pour l'analyse directe pour l'instant. "
            "Seuls les textes JORF, LEGI, LODA et CODE sont connectés."
        ),
        "origin": clean_origin,
        "text_id": text_id,
    }


def consult_best_available_text(text_id: str, origin: str) -> dict:
    clean_origin = origin.strip().upper()
    clean_text_id = text_id.split("_")[0]

    if clean_origin in ["LEGI", "CODE", "LODA"]:
        legi_text = consult_legi_text(clean_text_id)

        return {
            "selected_origin": clean_origin,
            "resolved_origin": "LEGI",
            "text_id": text_id,
            "legi_id": clean_text_id,
            "jorf_text": None,
            "legi_text": legi_text,
            "jurisState": legi_text.get("jurisState"),
            "textAbroge": legi_text.get("textAbroge"),
            "resolution": {
                "resolved": True,
                "legi_id": clean_text_id,
                "message": "Texte déjà fourni en LEGI / LODA / CODE.",
            },
        }

    if clean_origin == "JORF":
        jorf_text = None
        jorf_error = None

        try:
            jorf_text = consult_jorf_text(clean_text_id)
        except Exception as e:
            jorf_error = str(e)

        jorf_cid = (
            jorf_text.get("cid")
            if jorf_text
            else clean_text_id
        )

        resolution = {
            "resolved": False,
            "legi_id": None,
            "message": "Résolution JORF vers LEGI non effectuée.",
        }

        try:
            resolution = resolve_jorf_to_legi(jorf_cid)
        except Exception as e:
            resolution = {
                "resolved": False,
                "legi_id": None,
                "message": "Résolution JORF vers LEGI impossible.",
                "error": str(e),
            }

        if resolution.get("resolved") and resolution.get("legi_id"):
            legi_id = resolution["legi_id"]

            try:
                legi_text = consult_legi_text(legi_id)

                return {
                    "selected_origin": "JORF",
                    "resolved_origin": "LEGI",
                    "text_id": text_id,
                    "legi_id": legi_id,
                    "jorf_text": jorf_text,
                    "legi_text": legi_text,
                    "jurisState": legi_text.get("jurisState"),
                    "textAbroge": legi_text.get("textAbroge"),
                    "resolution": resolution,
                }

            except Exception as e:
                return {
                    "selected_origin": "JORF",
                    "resolved_origin": "JORF" if jorf_text else None,
                    "text_id": text_id,
                    "legi_id": legi_id,
                    "jorf_text": jorf_text,
                    "legi_text": None,
                    "jurisState": jorf_text.get("jurisState") if jorf_text else None,
                    "textAbroge": jorf_text.get("textAbroge") if jorf_text else None,
                    "resolution": resolution,
                    "legi_error": str(e),
                }

        if jorf_text:
            return {
                "selected_origin": "JORF",
                "resolved_origin": "JORF",
                "text_id": text_id,
                "legi_id": None,
                "jorf_text": jorf_text,
                "legi_text": None,
                "jurisState": jorf_text.get("jurisState"),
                "textAbroge": jorf_text.get("textAbroge"),
                "resolution": resolution,
            }

        raise RuntimeError(
            f"Impossible de consulter le texte JORF. Détail : {jorf_error}"
        )

    return {
        "selected_origin": clean_origin,
        "resolved_origin": None,
        "text_id": text_id,
        "message": "Origine non supportée.",
    }


def search_loda(
    query: str,
    max_pages: int = 10,
    page_size: int = 50,
) -> list[dict]:
    query_lower = query.lower().strip()
    filtered_results = []

    for page_number in range(1, max_pages + 1):
        data = get_loda(page_number=page_number, page_size=page_size)

        for item in data.get("results", []):
            title = item.get("titre", "")

            if query_lower in title.lower():
                filtered_results.append({
                    "id": item.get("id"),
                    "cid": item.get("cid"),
                    "title": title,
                    "etat": item.get("etat"),
                    "dateDebut": item.get("dateDebut"),
                    "lastUpdate": item.get("lastUpdate"),
                })

    return filtered_results


def search_dossiers(query: str) -> list[dict]:
    data = get_dossiers()
    dossiers = data.get("dossiersLegislatifs", [])

    query_lower = query.lower().strip()
    results = []

    for dossier in dossiers:
        title = dossier.get("titre", "")
        dossier_type = dossier.get("type", "")
        date_creation = dossier.get("dateCreation", "")

        nested_texts = " ".join(
            item.get("libelleTexte", "")
            for item in dossier.get("dossiers", [])
        )

        searchable_text = " ".join([
            title,
            dossier_type,
            date_creation,
            nested_texts,
        ]).lower()

        if query_lower in searchable_text:
            results.append({
                "id": dossier.get("id"),
                "title": title,
                "type": dossier_type,
                "dateCreation": date_creation,
                "dateDerniereModification": dossier.get(
                    "dateDerniereModification"
                ),
            })

    return results


def build_search_filters(only_active: bool) -> list[dict]:
    return []


def search_legifrance_documents(
    query: str,
    page_number: int = 1,
    page_size: int = 10,
    fond: str = "ALL",
    zone: str = "ALL",
    exact: bool | str = False,
    only_active: bool | str = False,
) -> dict:
    clean_query = query.strip()
    clean_fond = fond.strip().upper()
    clean_zone = zone.strip().upper()

    type_champ = "TITLE" if clean_zone in ["TITLE", "TITRE"] else "ALL"
    type_recherche = "EXACTE" if normalize_bool(exact) else "UN_DES_MOTS"

    payload = {
        "fond": clean_fond,
        "recherche": {
            "operateur": "ET",
            "pageNumber": page_number,
            "pageSize": page_size,
            "sort": "PERTINENCE",
            "typePagination": "DEFAUT",
            "champs": [
                {
                    "typeChamp": type_champ,
                    "operateur": "ET",
                    "criteres": [
                        {
                            "typeRecherche": type_recherche,
                            "valeur": clean_query,
                            "operateur": "ET",
                        }
                    ],
                }
            ],
            "filtres": build_search_filters(normalize_bool(only_active)),
        },
    }

    response = requests.post(
        f"{BASE_URL}/search",
        headers=get_headers(),
        json=payload,
    )

    return {
        "status_code": response.status_code,
        "payload": payload,
        "body": response.json() if response.text else None,
    }


def normalize_search_result(item: dict) -> dict:
    title_data = item.get("titles", [{}])[0] if item.get("titles") else {}

    sections = item.get("sections", [])
    first_extract = ""

    if sections:
        extracts = sections[0].get("extracts", [])
        if extracts:
            values = extracts[0].get("values", [])
            if values:
                first_extract = values[0]

    origin = item.get("origin")
    nature = item.get("nature")
    status = item.get("etat") or title_data.get("legalStatus")

    return {
        "id": title_data.get("id"),
        "cid": title_data.get("cid"),
        "title": clean_html_marks(title_data.get("title")),
        "nature": nature,
        "origin": origin,
        "status": status,
        "date": item.get("datePublication") or item.get("date"),
        "source": f"Légifrance - {origin}",
        "extract": clean_html_marks(first_extract),
        "is_analyzable": origin in ["JORF", "LEGI", "CODE", "LODA"],
        "analysis_type": origin,
    }


def result_priority(item: dict) -> int:
    nature = (item.get("nature") or "").upper()
    origin = (item.get("origin") or "").upper()
    title = (item.get("title") or "").upper()

    if origin == "CONSTIT" or "CONSTITUTION" in title:
        return 1

    if origin == "CODE" or nature == "CODE" or title.startswith("CODE ") or " CODE " in title:
        return 2

    if nature == "LOI" or title.startswith("LOI "):
        return 3

    if nature in ["PROJET_LOI", "PROPOSITION_LOI"]:
        return 4

    if nature == "ORDONNANCE" or title.startswith("ORDONNANCE "):
        return 5

    if nature in ["DECRET", "DÉCRET"] or title.startswith("DECRET ") or title.startswith("DÉCRET "):
        return 6

    if nature in ["ARRETE", "ARRÊTÉ"] or title.startswith("ARRETE ") or title.startswith("ARRÊTÉ "):
        return 7

    if nature in ["CIRCULAIRE", "INSTRUCTION"] or origin == "CIRC":
        return 8

    if nature == "RAPPORT" or title.startswith("RAPPORT "):
        return 9

    if nature == "AVIS" or title.startswith("AVIS "):
        return 10

    return 99


def title_match_score(item: dict, query: str) -> int:
    title = (item.get("title") or "").lower()
    clean_query = query.strip().lower()

    score = 0

    # Correspondance exacte de toute la recherche
    if clean_query and clean_query in title:
        score -= 200

    # Numéro officiel type 2015-988, 2023-857, etc.
    official_numbers = re.findall(r"\b\d{4}-\d+\b", clean_query)

    for number in official_numbers:
        if number in title:
            score -= 500

    # Mots importants présents dans le titre
    words = [
        word
        for word in re.split(r"\s+", clean_query)
        if len(word) > 2
    ]

    for word in words:
        if word in title:
            score -= 20

    # Bonus si le titre commence par LOI lorsque la requête contient loi
    if "loi" in clean_query and title.startswith("loi "):
        score -= 100

    return score


def search_official_documents(
    query: str,
    page_number: int = 1,
    page_size: int = 10,
    fond: str = "ALL",
    zone: str = "ALL",
    nature: str = "ALL",
    exact: bool | str = False,
    only_active: bool | str = False,
) -> dict:
    clean_nature = nature.strip().upper()
    collected_results = []
    last_body = {}
    last_error = None

    pages_to_fetch = 1

    if clean_nature != "ALL":
        pages_to_fetch = 8

    for api_page in range(1, pages_to_fetch + 1):
        search_response = search_legifrance_documents(
            query=query,
            page_number=api_page,
            page_size=25,
            fond=fond,
            zone=zone,
            exact=exact,
            only_active=False,
        )

        body = search_response.get("body", {})
        last_body = body

        if search_response.get("status_code") != 200:
            last_error = {
                "error": body,
                "payload": search_response.get("payload"),
                "status_code": search_response.get("status_code"),
            }
            break

        page_results = [
            normalize_search_result(item)
            for item in body.get("results", [])
        ]

        collected_results.extend(page_results)

        if len(body.get("results", [])) == 0:
            break

    if last_error and not collected_results:
        return {
            "query": query.strip(),
            "fond": fond,
            "zone": zone,
            "nature": nature,
            "exact": normalize_bool(exact),
            "only_active": normalize_bool(only_active),
            "count": 0,
            "total": 0,
            "results": [],
            "facets": [],
            **last_error,
        }

    if normalize_bool(only_active):
        collected_results = [
            item
            for item in collected_results
            if (
                (item.get("status") or "").upper() == "VIGUEUR"
                or (item.get("origin") or "").upper() == "JORF"
            )
        ]

    if clean_nature != "ALL":
        collected_results = [
            item
            for item in collected_results
            if (item.get("nature") or "").upper() == clean_nature
        ]

    unique_results = {}

    for item in collected_results:
        key = item.get("id") or item.get("cid") or item.get("title")

        if key and key not in unique_results:
            unique_results[key] = item

    sorted_results = sorted(
    unique_results.values(),
    key=lambda item: (
        title_match_score(item, query),
        result_priority(item),
    ),
)

    start = (page_number - 1) * page_size
    end = start + page_size
    paginated_results = sorted_results[start:end]

    return {
        "query": query.strip(),
        "fond": fond,
        "zone": zone,
        "nature": nature,
        "exact": normalize_bool(exact),
        "only_active": normalize_bool(only_active),
        "page_number": page_number,
        "page_size": page_size,
        "count": len(paginated_results),
        "total": len(sorted_results),
        "results": paginated_results,
        "facets": last_body.get("facets", []),
    }


def search_multiple_fonds(
    query: str,
    zone: str = "ALL",
    nature: str = "ALL",
    exact: bool | str = False,
    only_active: bool | str = False,
    page_size: int = 10,
) -> dict:
    fonds_to_search = ["CODE", "LEGI", "JORF"]

    all_results = []
    total_by_fond = {}

    for fond in fonds_to_search:
        result = search_official_documents(
            query=query,
            fond=fond,
            zone=zone,
            nature=nature,
            exact=exact,
            only_active=False,
            page_number=1,
            page_size=page_size,
        )

        total_by_fond[fond] = result.get("total", 0)

        for item in result.get("results", []):
            all_results.append(item)

    unique_results = {}

    for item in all_results:
        key = item.get("id") or item.get("cid") or item.get("title")

        if key and key not in unique_results:
            unique_results[key] = item

    results = sorted(
    unique_results.values(),
    key=lambda item: (
        title_match_score(item, query),
        result_priority(item),
    ),
)

    return {
        "query": query.strip(),
        "fond": "PRIORITIZED",
        "zone": zone,
        "nature": nature,
        "exact": normalize_bool(exact),
        "only_active": normalize_bool(only_active),
        "count": len(results),
        "total_by_fond": total_by_fond,
        "results": results,
    }

def global_search(
    query: str,
    fund: str = "all",
    status: str = "all",
    zone: str = "all",
) -> dict:
    clean_query = query.strip()

    search_result = search_official_documents(
        query=clean_query,
        page_number=1,
        page_size=10,
        fond="ALL",
        zone=zone,
        nature="ALL",
        exact=False,
        only_active=status.strip().upper() == "VIGUEUR",
    )

    return {
        "query": clean_query,
        "filters": {
            "fund": fund.strip().lower(),
            "status": status.strip().upper(),
            "zone": zone.strip().lower(),
        },
        "count": search_result.get("count", 0),
        "total": search_result.get("total"),
        "results": search_result.get("results", []),
        "dossiers_legislatifs": search_dossiers(clean_query),
        "textes_loda": search_loda(
            clean_query,
            max_pages=20,
            page_size=100,
        ),
    }

def test_consult_endpoint(endpoint: str, text_id: str) -> dict:
    response = requests.post(
        f"{BASE_URL}{endpoint}",
        headers=get_headers(),
        json={"id": text_id},
    )

    return {
        "endpoint": endpoint,
        "status_code": response.status_code,
        "body": response.text[:2000],
    }

def consult_text_by_origin(text_id: str, origin: str) -> dict:
    clean_origin = origin.strip().upper()

    return {
        "origin": clean_origin,
        "text_id": text_id,
        "status_code": 200,
        "body": consult_text(text_id, clean_origin),
    }

def test_chrono_text_cid(text_cid: str) -> dict:
    endpoint = "/chrono/textCid"
    url = f"{BASE_URL}{endpoint}"

    payloads = [
        {"textCid": text_cid},
        {"cid": text_cid},
        {"id": text_cid},
        {"textId": text_cid},
    ]

    results = []

    for payload in payloads:
        response = requests.post(
            url,
            headers=get_headers(),
            json=payload,
        )

        results.append({
            "payload": payload,
            "status_code": response.status_code,
            "body": response.text[:3000],
        })

    return {
        "endpoint": endpoint,
        "text_cid": text_cid,
        "tests": results,
    }