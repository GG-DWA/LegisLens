from io import BytesIO
from datetime import datetime
import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    Image,
)
from reportlab.lib.units import cm


TECHNICAL_DATES = {"2999-01-01", "2222-02-22"}


def clean_text(value) -> str:
    return str(value or "").replace("\n", "<br/>")


def format_date(value: str | None) -> str:
    if not value or value in TECHNICAL_DATES:
        return ""

    try:
        year, month, day = value.split("-")
        return f"{day}/{month}/{year}"
    except ValueError:
        return value


def make_list(items, label_key="name", text_key="reason"):
    styles = getSampleStyleSheet()

    if not items:
        return Paragraph("Non précisé.", styles["BodyText"])

    return ListFlowable(
        [
            ListItem(
                Paragraph(
                    f"<b>{clean_text(item.get(label_key))}</b> — "
                    f"{clean_text(item.get(text_key))}",
                    styles["BodyText"],
                )
            )
            for item in items
        ],
        bulletType="bullet",
    )


def make_timeline(items):
    styles = getSampleStyleSheet()

    if not items:
        return Paragraph("Non précisé.", styles["BodyText"])

    return ListFlowable(
        [
            ListItem(
                Paragraph(
                    f"<b>{format_date(item.get('date')) or 'Aujourd’hui'} — "
                    f"{clean_text(item.get('label'))}</b><br/>"
                    f"{clean_text(item.get('description'))}",
                    styles["BodyText"],
                )
            )
            for item in items
        ],
        bulletType="bullet",
    )


def make_legal_changes_list(items):
    styles = getSampleStyleSheet()

    if not items:
        return Paragraph("Aucune disposition repérée.", styles["BodyText"])

    return ListFlowable(
        [
            ListItem(
                Paragraph(
                    f"<b>Article {clean_text(item.get('article'))}</b> — "
                    f"{clean_text(item.get('target'))}",
                    styles["BodyText"],
                )
            )
            for item in items
        ],
        bulletType="bullet",
    )


def extract_impacted_codes(legal_changes):
    codes = set()

    for change in legal_changes:
        target = change.get("target", "")

        match = re.match(r"(Code\s+.*?)(?=\s+Art\.|$)", target)

        if match:
            codes.add(match.group(1).strip().replace(".", ""))

    return sorted(codes)


def generate_analysis_pdf(data: dict) -> BytesIO:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    answer = data.get("answer", {})
    source = data.get("source", {})
    legal_changes = data.get("legal_changes", [])
    impacted_codes = extract_impacted_codes(legal_changes)
    timeline = data.get("parliamentary_path", {}).get("timeline", [])

    created_changes = [
        item for item in legal_changes
        if item.get("type") == "created"
    ]

    modified_changes = [
        item for item in legal_changes
        if item.get("type") == "modified"
    ]

    logo_path = os.path.join(
        "app",
        "static",
        "images",
        "logo-legislens.png",
    )

    if os.path.exists(logo_path):
        story.append(
            Image(
                logo_path,
                width=2.2 * cm,
                height=2.2 * cm,
            )
        )
        story.append(Spacer(1, 8))

    story.append(Paragraph("LegisLens", styles["Title"]))

    story.append(
        Paragraph(
            "Analyse citoyenne",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            "Comprendre rapidement l'empreinte d'un texte officiel",
            styles["Italic"],
        )
    )

    story.append(Spacer(1, 16))

    story.append(
        Paragraph(
            "Texte analysé",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            clean_text(data.get("query")),
            styles["Heading1"],
        )
    )

    story.append(Spacer(1, 12))

    story.append(Paragraph("Fiche d’identité", styles["Heading2"]))

    story.append(
        Paragraph(
            f"<b>Nature :</b> {clean_text(source.get('nature'))}",
            styles["BodyText"],
        )
    )

    story.append(
        Paragraph(
            f"<b>État juridique :</b> "
            f"{clean_text(data.get('jurisState') or source.get('jurisState'))}",
            styles["BodyText"],
        )
    )

    if data.get("legi_id"):
        story.append(
            Paragraph(
                f"<b>Identifiant LEGI :</b> {clean_text(data.get('legi_id'))}",
                styles["BodyText"],
            )
        )

    if source.get("cid"):
        story.append(
            Paragraph(
                f"<b>Identifiant JORF :</b> {clean_text(source.get('cid'))}",
                styles["BodyText"],
            )
        )

    if (
        source.get("dateDebutVersion")
        and source.get("dateDebutVersion") not in TECHNICAL_DATES
    ):
        story.append(
            Paragraph(
                "<b>Version analysée :</b> "
                f"version consolidée depuis le "
                f"{format_date(source.get('dateDebutVersion'))}",
                styles["BodyText"],
            )
        )

    story.append(Spacer(1, 12))

    story.append(Paragraph("Parcours du texte", styles["Heading2"]))
    story.append(make_timeline(timeline))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Vue d’ensemble", styles["Heading2"]))
    story.append(Paragraph(clean_text(answer.get("overview")), styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Acteurs concernés", styles["Heading2"]))
    story.append(make_list(answer.get("actors", []), "name", "reason"))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Secteurs impactés", styles["Heading2"]))
    story.append(make_list(answer.get("impacted_sectors", []), "name", "reason"))
    story.append(Spacer(1, 12))

    if impacted_codes:
        story.append(Paragraph("Codes impactés", styles["Heading2"]))

        story.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(
                            clean_text(code),
                            styles["BodyText"],
                        )
                    )
                    for code in impacted_codes
                ],
                bulletType="bullet",
            )
        )

        story.append(Spacer(1, 12))

    story.append(Paragraph("Ce qui change concrètement", styles["Heading2"]))
    story.append(make_list(answer.get("concrete_changes", []), "title", "description"))
    story.append(Spacer(1, 12))

    if legal_changes:
        story.append(Paragraph("Articles créés ou modifiés", styles["Heading2"]))

        if created_changes:
            story.append(Paragraph("Dispositions créées", styles["Heading3"]))
            story.append(make_legal_changes_list(created_changes))
            story.append(Spacer(1, 8))

        if modified_changes:
            story.append(Paragraph("Dispositions modifiées", styles["Heading3"]))
            story.append(make_legal_changes_list(modified_changes[:10]))

            if len(modified_changes) > 10:
                story.append(
                    Paragraph(
                        f"{len(modified_changes) - 10} autre(s) modification(s) "
                        "non affichée(s) dans cette synthèse.",
                        styles["Italic"],
                    )
                )

        story.append(Spacer(1, 12))

    story.append(Paragraph("Points d’attention", styles["Heading2"]))
    story.append(make_list(answer.get("attention_points", []), "title", "description"))
    story.append(Spacer(1, 12))

    if answer.get("limits"):
        story.append(Paragraph("Limites de l’analyse", styles["Heading2"]))
        story.append(Paragraph(clean_text(answer.get("limits")), styles["BodyText"]))
        story.append(Spacer(1, 12))

    story.append(Paragraph("Sources officielles", styles["Heading2"]))
    story.append(Paragraph(clean_text(source.get("title")), styles["BodyText"]))

    if source.get("jorfText"):
        story.append(
            Paragraph(
                clean_text(source.get("jorfText")),
                styles["BodyText"],
            )
        )

    story.append(Spacer(1, 12))

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")

    story.append(
        Paragraph(
            "Analyse générée automatiquement à partir des données officielles. "
            f"LegisLens — {generated_at}",
            styles["Italic"],
        )
    )

    doc.build(story)
    buffer.seek(0)

    return buffer