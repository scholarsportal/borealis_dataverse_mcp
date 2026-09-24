from borealis_toolkit.quality import (
    assess_dataverse_metadata,
    grade_for_score,
    recommendation_for,
    score_variable_coverage,
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


def test_assess_dataverse_metadata_prefers_exact_local_name_over_substring():
    # Real Borealis exports carry both; an empty 'title' must not be rescued by 'alternativeTitle'.
    metadata = {"citation:alternativeTitle": "CES", "title": ""}
    assert "title" in assess_dataverse_metadata(metadata)["missing_fields"]

    metadata = {"citation:alternativeTitle": "", "title": "Canadian Election Study"}
    assert "title" in assess_dataverse_metadata(metadata)["present_fields"]


def test_assess_dataverse_metadata_falls_back_to_substring_match():
    metadata = {"geospatial:geographicCoverageOther": "Canada"}
    assert "geographic_coverage" in assess_dataverse_metadata(metadata)["present_fields"]


def test_score_variable_coverage_full_credit():
    coverage = {"variables": 4, "labelled": 4, "categorical": 2, "value_labelled": 2, "with_question_text": 4}
    points, recs = score_variable_coverage(coverage)
    assert points == 10
    assert recs == []


def test_score_variable_coverage_partial_credit_and_messages():
    coverage = {"variables": 10, "labelled": 10, "categorical": 4, "value_labelled": 2, "with_question_text": 0}
    points, recs = score_variable_coverage(coverage)
    assert points == 5 + 1.5 + 0
    assert [r["priority"] for r in recs] == ["medium", "low"]
    assert "2 of 4 categorical" in recs[0]["message"]
    assert "10 of 10 variables lack question text" in recs[1]["message"]


def test_score_variable_coverage_no_categorical_variables_is_not_penalized():
    coverage = {"variables": 2, "labelled": 2, "categorical": 0, "value_labelled": 0, "with_question_text": 2}
    assert score_variable_coverage(coverage)[0] == 10


def test_score_variable_coverage_no_variables_scores_zero():
    points, recs = score_variable_coverage({"variables": 0})
    assert points == 0
    assert recs[0]["field"] == "variable_metadata"
