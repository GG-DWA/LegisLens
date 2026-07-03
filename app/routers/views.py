from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.services.legifrance import get_dossier_detail
from app.services.impact_analyzer import extract_sources
from app.services.llm_analyzer import analyze_with_llm
from app.services.parliamentary_tracker import extract_parliamentary_stage

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )


@router.get("/law/{dossier_id}")
def law_detail(request: Request, dossier_id: str):
    dossier = get_dossier_detail(dossier_id)

    dossier_data = dossier.get("dossierLegislatif", {})

    sources = extract_sources(
        dossier_data.get("arborescence", {})
    )

    impact = analyze_with_llm(
        dossier_data,
        sources
    )

    stage = extract_parliamentary_stage(dossier)

    return templates.TemplateResponse(
        request=request,
        name="law_detail.html",
        context={
            "dossier_id": dossier_id,
            "impact": impact,
            "stage": stage,
        }
    )