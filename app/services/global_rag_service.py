from app.services.legifrance import global_search, get_dossier_detail
from app.services.impact_analyzer import extract_sources
from app.services.document_loader import download_and_extract_pdf
from app.services.rag_service import build_rag_index, search_rag
from app.services.global_llm_service import build_citizen_answer


def build_global_corpus(query: str) -> dict:
    results = global_search(query)

    corpus = []

    for dossier in results.get("dossiers_legislatifs", []):
        corpus.append({
            "type": "dossier",
            "id": dossier.get("id"),
            "title": dossier.get("title"),
            "source": "dossier_legislatif",
        })

    for text in results.get("textes_loda", []):
        corpus.append({
            "type": "loda",
            "id": text.get("id"),
            "cid": text.get("cid"),
            "title": text.get("title"),
            "etat": text.get("etat"),
            "source": "loda",
        })

    return {
        "query": query.strip(),
        "count": len(corpus),
        "corpus": corpus,
    }


def search_global_dossier_pdfs(query: str) -> dict:
    search_results = global_search(query)

    corpus_text = ""
    used_sources = []

    for dossier in search_results.get("dossiers_legislatifs", [])[:3]:
        try:
            detail = get_dossier_detail(dossier.get("id"))
            dossier_data = detail.get("dossierLegislatif", {})

            sources = extract_sources(
                dossier_data.get("arborescence", {})
            )

            for source in sources:
                label = source.get("label", "")
                url = source.get("url", "")

                if (
                    label in [
                        "Projet de loi",
                        "Exposé des motifs",
                        "Etude d'impact",
                        "Avis du Conseil d'Etat",
                    ]
                    and url.endswith(".pdf")
                ):
                    text = download_and_extract_pdf(
                        url,
                        f"{dossier.get('id')}_{label}.pdf"
                    )

                    corpus_text += (
                        f"\n\n===== {dossier.get('title')} | {label} =====\n\n"
                        + text[:12000]
                    )

                    used_sources.append({
                        "dossier_id": dossier.get("id"),
                        "title": dossier.get("title"),
                        "label": label,
                        "url": url,
                    })

        except Exception as e:
            print(f"Erreur dossier {dossier.get('id')}: {e}")

    if not corpus_text.strip():
        return {
            "query": query.strip(),
            "sources": used_sources,
            "results": [],
            "message": "Aucun contenu PDF exploitable trouvé dans les dossiers législatifs."
        }

    store = build_rag_index(corpus_text)

    results = search_rag(
        store,
        query
    )

    return {
        "query": query.strip(),
        "sources": used_sources,
        "results": results,
    }

def analyze_topic(query: str) -> dict:
    search_results = global_search(query)

    rag_result = search_global_dossier_pdfs(query)

    chunks = rag_result.get("results", [])

    if not chunks:
        return {
            "query": query.strip(),
            "answer": {
                "overview": "Aucun passage pertinent n'a été trouvé dans les documents disponibles.",
                "actors": [],
                "concrete_changes": [],
                "attention_points": [],
                "limits": "L'analyse n'a pas pu être produite car aucun contenu exploitable n'a été trouvé."
            },
            "sources": rag_result.get("sources", []),
            "legal_texts_found": search_results.get("textes_loda", []),
            "chunks": [],
        }

    answer = build_citizen_answer(
        query=query,
        rag_chunks=chunks
    )

    return {
        "query": query.strip(),
        "answer": answer,
        "sources": rag_result.get("sources", []),
        "legal_texts_found": search_results.get("textes_loda", []),
        "chunks": chunks[:5],
    }

def analyze_dossier_by_id(dossier_id: str) -> dict:
    detail = get_dossier_detail(dossier_id)
    dossier_data = detail.get("dossierLegislatif", {})

    title = dossier_data.get("titre", dossier_id)

    sources = extract_sources(
        dossier_data.get("arborescence", {})
    )

    corpus_text = ""
    used_sources = []

    for source in sources:
        label = source.get("label", "")
        url = source.get("url", "")

        if (
            label in [
                "Projet de loi",
                "Exposé des motifs",
                "Etude d'impact",
                "Avis du Conseil d'Etat",
            ]
            and url.endswith(".pdf")
        ):
            try:
                text = download_and_extract_pdf(
                    url,
                    f"{dossier_id}_{label}.pdf"
                )

                corpus_text += (
                    f"\n\n===== {title} | {label} =====\n\n"
                    + text[:12000]
                )

                used_sources.append({
                    "dossier_id": dossier_id,
                    "title": title,
                    "label": label,
                    "url": url,
                })

            except Exception as e:
                print(f"Erreur PDF {label}: {e}")

    if not corpus_text.strip():
        return {
            "query": title,
            "answer": {
                "overview": "Aucun document PDF exploitable n'a été trouvé pour ce dossier.",
                "actors": [],
                "impacted_sectors": [],
                "law_footprint": [],
                "concrete_changes": [],
                "attention_points": [],
                "official_sources_summary": "",
                "limits": "L'analyse n'a pas pu être produite car aucun document exploitable n'a été trouvé."
            },
            "sources": used_sources,
            "legal_texts_found": [],
            "chunks": [],
        }

    store = build_rag_index(corpus_text)

    chunks = search_rag(
        store,
        title
    )

    answer = build_citizen_answer(
        query=title,
        rag_chunks=chunks
    )

    return {
        "query": title,
        "dossier_id": dossier_id,
        "answer": answer,
        "sources": used_sources,
        "legal_texts_found": [],
        "chunks": chunks[:5],
    }