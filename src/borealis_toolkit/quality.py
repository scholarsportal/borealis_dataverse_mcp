from __future__ import annotations

from typing import Any

# Each spec scores one DDI-relevant field out of a Dataverse dataset's exported
# metadata. Different Dataverse installs prefix fields with different
# metadata-block namespaces (e.g. 'citation:', 'socialscience:', 'geospatial:')
# depending on which blocks they enable, so `match` names are compared against
# each top-level key's local name (after the last ':'), case-insensitively.
# An exact local-name match wins; a substring match is only the fallback, so
# 'title' finds 'title' rather than 'alternativeTitle' or 'seriesTitle'.
_FIELD_SPECS: list[dict[str, Any]] = [
    {"key": "title", "weight": 5, "category": "discovery", "match": ["title"]},
    {"key": "author", "weight": 5, "category": "discovery", "match": ["author"]},
    {"key": "description", "weight": 10, "category": "discovery", "match": ["dsdescription"], "min_length": 100},
    {"key": "keywords", "weight": 8, "category": "discovery", "match": ["keyword"], "min_count": 3},
    {"key": "related_publications", "weight": 5, "category": "discovery", "match": ["publication"]},
    {"key": "date_of_collection", "weight": 7, "category": "coverage", "match": ["dateofcollection"]},
    {"key": "geographic_coverage", "weight": 7, "category": "coverage", "match": ["geographiccoverage", "geographicunit"]},
    {"key": "unit_of_analysis", "weight": 8, "category": "coverage", "match": ["unitofanalysis"]},
    {"key": "universe", "weight": 8, "category": "coverage", "match": ["universe"]},
    {"key": "time_period_covered", "weight": 7, "category": "coverage", "match": ["timeperiodcovered"]},
    {"key": "data_collection_method", "weight": 8, "category": "methodology", "match": ["collectionmode", "typeofdatacollection", "researchinstrument"]},
    {"key": "sampling_procedure", "weight": 7, "category": "methodology", "match": ["samplingprocedure"]},
    {"key": "license", "weight": 6, "category": "access", "match": ["license"]},
    {"key": "file_format_documented", "weight": 5, "category": "access", "match": ["kindofdata"]},
]

VARIABLE_METADATA_WEIGHT = 10
VARIABLE_METADATA_CATEGORY = "access"

# Share of VARIABLE_METADATA_WEIGHT earned by each kind of variable-level documentation.
_VARIABLE_COVERAGE_WEIGHTS = {"labels": 5, "value_labels": 3, "question_text": 2}

_RECOMMENDATIONS: dict[str, str] = {
    "title": "Add a descriptive title. It is the primary field used for discovery and citation.",
    "author": "Add at least one author with name and affiliation.",
    "description": "Write a fuller abstract/description (aim for 100+ characters) so reusers understand what the data measures.",
    "keywords": "Add at least 3 keyword/subject terms so the dataset surfaces in topic search.",
    "related_publications": "Link to related publications (DOIs preferred). Increases discoverability and citation.",
    "date_of_collection": "Record the date(s) data collection took place. Distinct from the publication date, this tells reusers how current the data is.",
    "geographic_coverage": "Document the geographic coverage (country/region/unit) the data describes.",
    "unit_of_analysis": "Add the unit of analysis (e.g. 'Individual respondents'). This is a core DDI field required for informed reuse.",
    "universe": "Describe the universe/population studied — who was eligible to be observed, surveyed, or sampled.",
    "time_period_covered": "Note the time period the data covers, which may differ from the collection date.",
    "data_collection_method": "Document the data collection method (survey, interview, administrative records, etc.).",
    "sampling_procedure": "Document the sampling procedure. Without this, users cannot assess representativeness.",
    "license": "Add a license (e.g. CC-BY) so reusers know their rights.",
    "file_format_documented": "Note the original file format(s) contributed (e.g. SPSS, Stata), not just the archival .tab conversion.",
    "variable_metadata": "Add variable-level DDI documentation (labels, value labels, question text) — the richest reuse signal in a dataset.",
    "variable_labels": "{missing} of {total} variables lack a label. Variable labels are the minimum reusers need to know what each column measures.",
    "variable_value_labels": "{missing} of {total} categorical variables lack value labels, so their codes cannot be interpreted without the codebook.",
    "variable_question_text": "{missing} of {total} variables lack question text. Adding the literal question wording helps reusers compare across surveys.",
}

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _priority_for_weight(weight: int) -> str:
    if weight >= 7:
        return "high"
    if weight >= 5:
        return "medium"
    return "low"


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        return " ".join(_stringify(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_stringify(v) for v in value)
    return str(value)


def _count_entries(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0 if value in (None, "", {}) else 1


def recommendation_for(field_key: str, **values: Any) -> str:
    message = _RECOMMENDATIONS[field_key]
    return message.format(**values) if values else message


def _find_key(keys: list[str], names: list[str]) -> str | None:
    local = {key: key.rsplit(":", 1)[-1].lower() for key in keys}
    for key in keys:
        if local[key] in names:
            return key
    return next((key for key in keys if any(name in local[key] for name in names)), None)


def score_variable_coverage(coverage: dict[str, int]) -> tuple[float, list[dict[str, str]]]:
    """Partial credit out of VARIABLE_METADATA_WEIGHT for variable-level documentation.

    Labels, value labels (among categorical variables only) and question text
    each earn their share in proportion to how many variables carry them. A
    component with nothing to measure (e.g. no categorical variables) earns
    full credit rather than penalizing the dataset.
    Returns (points, recommendations for the incomplete components).
    """
    total = coverage.get("variables", 0)
    if total == 0:
        return 0.0, [{"priority": "high", "field": "variable_metadata", "message": recommendation_for("variable_metadata")}]

    components = [
        ("labels", "variable_labels", coverage.get("labelled", 0), total, "high"),
        ("value_labels", "variable_value_labels", coverage.get("value_labelled", 0), coverage.get("categorical", 0), "medium"),
        ("question_text", "variable_question_text", coverage.get("with_question_text", 0), total, "low"),
    ]
    points = 0.0
    recommendations: list[dict[str, str]] = []
    for component, rec_key, have, denominator, priority in components:
        ratio = have / denominator if denominator else 1.0
        points += _VARIABLE_COVERAGE_WEIGHTS[component] * ratio
        if ratio < 1.0:
            recommendations.append({
                "priority": priority,
                "field": "variable_metadata",
                "message": recommendation_for(rec_key, missing=denominator - have, total=denominator),
            })
    return round(points, 1), recommendations


def sort_recommendations(recommendations: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(recommendations, key=lambda r: _PRIORITY_ORDER[r["priority"]])


def assess_dataverse_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Score a Dataverse dataset's exported metadata against a DDI-informed
    completeness rubric. Field presence is judged by top-level key name only,
    so nested parent-collection metadata (schema:isPartOf, @context, ...)
    never gets mistaken for the dataset's own fields.
    """
    keys = list(metadata)
    breakdown: dict[str, dict[str, Any]] = {}
    present: list[str] = []
    missing: list[str] = []
    recommendations: list[dict[str, str]] = []
    earned = 0
    max_total = 0

    for spec in _FIELD_SPECS:
        category = breakdown.setdefault(spec["category"], {"score": 0, "max": 0, "fields": []})
        category["max"] += spec["weight"]
        category["fields"].append(spec["key"])
        max_total += spec["weight"]

        matched_key = _find_key(keys, spec["match"])
        value = metadata.get(matched_key) if matched_key else None
        present_ok = matched_key is not None and value not in (None, "", [], {})
        if present_ok and "min_length" in spec:
            present_ok = len(_stringify(value)) >= spec["min_length"]
        if present_ok and "min_count" in spec:
            present_ok = _count_entries(value) >= spec["min_count"]

        if present_ok:
            present.append(spec["key"])
            category["score"] += spec["weight"]
            earned += spec["weight"]
        else:
            missing.append(spec["key"])
            recommendations.append({
                "priority": _priority_for_weight(spec["weight"]),
                "field": spec["key"],
                "message": recommendation_for(spec["key"]),
            })

    return {
        "breakdown": breakdown,
        "present_fields": present,
        "missing_fields": missing,
        "recommendations": sort_recommendations(recommendations),
        "earned": earned,
        "max_total": max_total,
    }


def grade_for_score(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"
