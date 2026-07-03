import re
from datetime import datetime, timezone


MONTHS_FR = {
    "janvier": "01",
    "février": "02",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "août": "08",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "décembre": "12",
    "decembre": "12",
}

TECHNICAL_OPEN_DATES = {"2999-01-01", "2222-02-22"}


def timestamp_to_date(value) -> str:
    if not value:
        return ""

    if isinstance(value, str):
        return clean_technical_date(value)

    if isinstance(value, int):
        try:
            return datetime.fromtimestamp(
                value / 1000,
                tz=timezone.utc,
            ).strftime("%Y-%m-%d")
        except (OSError, OverflowError, ValueError):
            return ""

    return ""


def clean_technical_date(value: str | None) -> str:
    if not value:
        return ""

    value = str(value).strip()

    if value in TECHNICAL_OPEN_DATES:
        return ""

    return value


def extract_date_from_title(title: str) -> str:
    if not title:
        return ""

    match = re.search(
        r"du\s+(\d{1,2})\s+([a-zéûôîàèùç]+)\s+(\d{4})",
        title.lower(),
    )

    if not match:
        return ""

    day, month_label, year = match.groups()
    month = MONTHS_FR.get(month_label)

    if not month:
        return ""

    return f"{year}-{month}-{int(day):02d}"


def build_parliamentary_path(source: dict | None) -> dict:
    if not source:
        return {
            "steps": [],
            "timeline": [],
        }

    title = source.get("title", "")
    nature = source.get("nature", "")
    jorf_text = source.get("jorfText", "")
    juris_state = source.get("jurisState", "")

    date_debut = clean_technical_date(source.get("dateDebutVersion", ""))
    date_fin = clean_technical_date(source.get("dateFinVersion", ""))

    display_version = bool(date_debut)

    promulgation_date = (
        timestamp_to_date(source.get("dateTexte"))
        or extract_date_from_title(title)
    )

    publication_date = timestamp_to_date(source.get("dateParution"))

    current_version_description = (
        f"Fin de version : {date_fin}"
        if date_fin
        else "Texte actuellement en vigueur."
    )

    steps = [
        {
            "label": "Texte adopté",
            "status": "done",
            "description": title,
        },
        {
            "label": "Promulgation",
            "status": "done" if promulgation_date else "unknown",
            "description": (
                f"{nature} promulgué le {promulgation_date}."
                if promulgation_date
                else f"{nature} promulgué à une date non précisée."
            ),
        },
        {
            "label": "Publication au Journal officiel",
            "status": "done" if jorf_text else "unknown",
            "description": jorf_text or "Publication non précisée.",
        },
        {
            "label": "Version consolidée",
            "status": "done" if juris_state else "unknown",
            "description": f"État juridique : {juris_state or 'non précisé'}",
        },
        {
            "label": "Version en vigueur",
            "status": "done" if juris_state.lower() == "vigueur" else "unknown",
            "description": (
                f"Depuis le {date_debut}"
                if display_version
                else "Texte actuellement en vigueur."
            ),
        },
    ]

    timeline = [
        {
            "date": promulgation_date,
            "label": "Promulgation",
            "description": title,
        },
        {
            "date": publication_date,
            "label": "Publication au Journal officiel",
            "description": jorf_text or "Publication non précisée.",
        },
    ]

    if display_version:
        timeline.append(
            {
                "date": date_debut,
                "label": "Début de la version analysée",
                "description": f"État juridique : {juris_state or 'non précisé'}",
            }
        )

    timeline.append(
        {
            "date": "",
            "label": "Version actuellement en vigueur",
            "description": current_version_description,
        }
    )

    timeline = [
        item
        for item in timeline
        if item.get("date") or item.get("description")
    ]

    return {
        "steps": steps,
        "timeline": timeline,
    }