def extract_parliamentary_stage(dossier: dict) -> dict:
    dossier_data = dossier.get("dossierLegislatif", {})
    arborescence = dossier_data.get("arborescence", {})

    stages = []
    institutions = set()

    def walk(node: dict):
        label = node.get("libelle", "").strip()

        if label:
            stages.append(label)

            if "Assemblée nationale" in label:
                institutions.add("Assemblée nationale")

            if "Sénat" in label:
                institutions.add("Sénat")

            if "Commission" in label or "commission" in label:
                institutions.add("Commission")

        for child in node.get("niveaux", []):
            walk(child)

    walk(arborescence)

    def detect_current_stage(stages: list[str]) -> str:
        """
        Recherche la dernière véritable étape parlementaire
        et ignore les éléments génériques comme :
        - Panorama des lois
        - Documents préparatoires
        - Débats parlementaires
        """

        ignored = {
            "Panorama des lois",
            "Documents préparatoires",
            "Débats parlementaires",
            "Dossiers législatifs",
        }

        for stage in reversed(stages):

            if stage in ignored:
                continue

            if (
                "Assemblée nationale" in stage
                or "Sénat" in stage
                or "Commission" in stage
                or "lecture" in stage.lower()
            ):
                return stage

        return stages[-1] if stages else ""

    current_stage = detect_current_stage(stages)

    return {
        "current_stage": current_stage,
        "institutions": sorted(list(institutions)),
        "known_steps": stages,
        "status": "Parcours identifié à partir du dossier législatif"
    }