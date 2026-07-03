from app.services.legifrance import get_dossier_detail
from app.services.parliamentary_tracker import extract_parliamentary_stage


def extract_dossier_id_from_text(text_data: dict) -> str | None:
    dossiers = text_data.get("dossiersLegislatifs", [])

    if not dossiers:
        return None

    first_dossier = dossiers[0]

    return first_dossier.get("id")


def build_real_parliamentary_path(text_data: dict) -> dict:
    dossier_id = extract_dossier_id_from_text(text_data)

    if not dossier_id:
        return {
            "available": False,
            "dossier_id": None,
            "steps": [],
            "message": "Aucun dossier législatif associé trouvé dans le texte.",
        }

    try:
        dossier_detail = get_dossier_detail(dossier_id)
    except Exception as e:
        return {
            "available": False,
            "dossier_id": dossier_id,
            "steps": [],
            "message": f"Dossier législatif trouvé, mais impossible à récupérer : {str(e)}",
        }

    try:
        stage = extract_parliamentary_stage(dossier_detail)
    except Exception as e:
        return {
            "available": False,
            "dossier_id": dossier_id,
            "steps": [],
            "message": f"Dossier récupéré, mais parcours impossible à extraire : {str(e)}",
        }

    return {
        "available": True,
        "dossier_id": dossier_id,
        "steps": stage,
        "message": "Parcours parlementaire réel récupéré depuis le dossier législatif.",
    }