from borealis_toolkit.quality import (
    assess_dataverse_metadata,
    grade_for_score,
    recommendation_for,
    sort_recommendations,
)


def test_assess_dataverse_metadata_matches_fields_case_insensitively_by_substring():
    metadata = {
        "citation:title": "A dataset",
        "citation:author": [{"citation:authorName": "A. Researcher"}],
        "schema:license": "CC-BY",
    }
    result = assess_dataverse_metadata(metadata)
    assert "title" in result["present_fields"]
    assert "author" in result["present_fields"]
    assert "license" in result["present_fields"]
    assert "description" in result["missing_fields"]
    assert result["earned"] < result["max_total"]


def test_assess_dataverse_metadata_enforces_min_length_and_min_count():
    metadata = {
        "citation:dsDescription": {"citation:dsDescriptionValue": "too short"},
        "citation:keyword": [{"citation:keywordValue": "one"}, {"citation:keywordValue": "two"}],
    }
    result = assess_dataverse_metadata(metadata)
    assert "description" in result["missing_fields"]
    assert "keywords" in result["missing_fields"]


def test_assess_dataverse_metadata_ignores_falsy_but_present_values():
    metadata = {"citation:title": "", "citation:author": [], "citation:keyword": None}
    result = assess_dataverse_metadata(metadata)
    assert "title" in result["missing_fields"]
    assert "author" in result["missing_fields"]
    assert "keywords" in result["missing_fields"]


def test_sort_recommendations_orders_high_before_medium_before_low():
    recs = [
        {"priority": "low", "field": "a", "message": "x"},
        {"priority": "high", "field": "b", "message": "y"},
        {"priority": "medium", "field": "c", "message": "z"},
    ]
    ordered = sort_recommendations(recs)
    assert [r["priority"] for r in ordered] == ["high", "medium", "low"]


def test_recommendation_for_known_field():
    assert "variable-level" in recommendation_for("variable_metadata").lower()


def test_grade_for_score_boundaries():
    assert grade_for_score(100) == "A"
    assert grade_for_score(90) == "A"
    assert grade_for_score(89) == "B"
    assert grade_for_score(75) == "B"
    assert grade_for_score(74) == "C"
    assert grade_for_score(60) == "C"
    assert grade_for_score(59) == "D"
    assert grade_for_score(45) == "D"
    assert grade_for_score(44) == "F"
    assert grade_for_score(0) == "F"
