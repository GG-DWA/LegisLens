from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.pdf_export_service import generate_analysis_pdf

from app.services.legifrance import (
    ping_legifrance,
    get_dossiers,
    get_dossier_detail,
    get_loda,
    get_loda_detail,
    search_dossiers,
    search_loda,
    global_search,
    test_consult_endpoint,
    search_legifrance_documents,
    search_official_documents,
    consult_jorf_text,
    consult_text,
    search_multiple_fonds,
    consult_best_available_text,
    test_chrono_text_cid,
)

from app.services.impact_analyzer import (
    analyze_dossier,
    extract_sources,
)

from app.services.citizen_text_analyzer import analyze_text_by_id
from app.services.parliamentary_tracker import extract_parliamentary_stage
from app.services.document_loader import download_and_extract_pdf
from app.services.rag_service import build_rag_index, search_rag

from app.services.global_rag_service import (
    build_global_corpus,
    search_global_dossier_pdfs,
    analyze_topic,
    analyze_dossier_by_id,
)


router = APIRouter(prefix="/api", tags=["laws"])


@router.get("/ping-legifrance")
def ping():
    try:
        return {
            "status": "ok",
            "response": ping_legifrance(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dossiers")
def dossiers():
    try:
        return get_dossiers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dossiers/{dossier_id}")
def dossier_detail(dossier_id: str):
    try:
        return get_dossier_detail(dossier_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/loda")
def loda(page_number: int = 1, page_size: int = 5):
    try:
        return get_loda(
            page_number=page_number,
            page_size=page_size,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/loda/{text_id}")
def loda_detail(text_id: str):
    try:
        return get_loda_detail(text_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de récupérer le détail LODA : {str(e)}",
        )


@router.get("/search-loda")
def search_loda_route(query: str):
    return search_loda(query)


@router.get("/search")
def search(query: str):
    return search_dossiers(query)


@router.get("/global-search")
def global_search_route(query: str):
    return global_search(query)


@router.get("/official-search")
def official_search(
    query: str,
    fund: str = "all",
    status: str = "all",
    zone: str = "all",
):
    return global_search(
        query=query,
        fund=fund,
        status=status,
        zone=zone,
    )


@router.get("/official-search-v2")
def official_search_v2(
    query: str,
    fond: str = "ALL",
    zone: str = "ALL",
    nature: str = "ALL",
    exact: bool = False,
    only_active: bool = False,
    page_number: int = 1,
    page_size: int = 10,
):
    return search_official_documents(
        query=query,
        fond=fond,
        zone=zone,
        nature=nature,
        exact=exact,
        only_active=only_active,
        page_number=page_number,
        page_size=page_size,
    )


@router.get("/official-search-prioritized")
def official_search_prioritized(
    query: str,
    zone: str = "ALL",
    nature: str = "ALL",
    exact: bool = False,
    only_active: bool = False,
    page_size: int = 10,
):
    return search_multiple_fonds(
        query=query,
        zone=zone,
        nature=nature,
        exact=exact,
        only_active=only_active,
        page_size=page_size,
    )


@router.get("/impact/{dossier_id}")
def impact(dossier_id: str):
    try:
        dossier = get_dossier_detail(dossier_id)
        return analyze_dossier(dossier)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parliamentary-stage/{dossier_id}")
def parliamentary_stage(dossier_id: str):
    try:
        dossier = get_dossier_detail(dossier_id)
        return extract_parliamentary_stage(dossier)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag-search/{dossier_id}")
def rag_search(dossier_id: str, query: str):
    try:
        dossier = get_dossier_detail(dossier_id)

        dossier_data = dossier.get("dossierLegislatif", {})

        sources = extract_sources(
            dossier_data.get("arborescence", {})
        )

        pdf_source = None

        for source in sources:
            if (
                source.get("label") == "Projet de loi"
                and source.get("url", "").endswith(".pdf")
            ):
                pdf_source = source
                break

        if not pdf_source:
            return {
                "query": query,
                "results": [],
                "message": "Aucun PDF Projet de loi trouvé.",
            }

        text = download_and_extract_pdf(
            pdf_source["url"],
            f"{dossier_id}_projet_de_loi.pdf",
        )

        store = build_rag_index(text)

        results = search_rag(
            store,
            query,
        )

        return {
            "dossier_id": dossier_id,
            "query": query,
            "source": pdf_source,
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/global-rag")
def global_rag(query: str):
    return build_global_corpus(query)


@router.get("/global-rag-search")
def global_rag_search(query: str):
    return search_global_dossier_pdfs(query)


@router.get("/citizen-analysis")
def citizen_analysis(query: str):
    return analyze_topic(query)


@router.get("/citizen-analysis/dossier/{dossier_id}")
def citizen_analysis_dossier(dossier_id: str):
    return analyze_dossier_by_id(dossier_id)


@router.get("/citizen-analysis/text/{text_id}")
def citizen_analysis_text(text_id: str, origin: str = "JORF"):
    return analyze_text_by_id(
        text_id=text_id,
        origin=origin,
    )


@router.get("/consult-text")
def consult_text_route(
    text_id: str,
    origin: str,
):
    try:
        return consult_text(
            text_id=text_id,
            origin=origin,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de consulter le texte : {str(e)}",
        )


@router.get("/consult-jorf-text")
def consult_jorf_text_route(text_cid: str):
    try:
        return consult_jorf_text(text_cid)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de consulter le texte JORF : {str(e)}",
        )


@router.get("/consult-best-text")
def consult_best_text_route(text_id: str, origin: str):
    try:
        return consult_best_available_text(
            text_id=text_id,
            origin=origin,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de consulter le meilleur texte disponible : {str(e)}",
        )


@router.get("/test-consult")
def test_consult(endpoint: str, text_id: str):
    return test_consult_endpoint(
        endpoint=endpoint,
        text_id=text_id,
    )



@router.get("/test-search")
def test_search(
    query: str,
    fond: str = "ALL",
    zone: str = "ALL",
    nature: str = "ALL",
    exact: bool = False,
    only_active: bool = False,
    page_number: int = 1,
    page_size: int = 10,
):
    return search_legifrance_documents(
        query=query,
        fond=fond,
        zone=zone,
        exact=exact,
        only_active=only_active,
        page_number=page_number,
        page_size=page_size,
    )

@router.get("/test-chrono-text-cid")
def test_chrono_text_cid_route(text_cid: str):
    return test_chrono_text_cid(text_cid)

@router.get("/citizen-analysis/pdf/{text_id}")
def citizen_analysis_pdf(text_id: str, origin: str = "LEGI"):
    analysis = analyze_text_by_id(text_id=text_id, origin=origin)
    pdf_buffer = generate_analysis_pdf(analysis)

    filename = f"legislens-analyse-{text_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )