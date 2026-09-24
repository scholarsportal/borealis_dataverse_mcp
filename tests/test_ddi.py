import pytest

from borealis_toolkit.ddi import documentation_coverage, parse_ddi_variables
from borealis_toolkit.errors import BorealisError

_NO_DATA_DSCR_XML = """<?xml version='1.0' encoding='UTF-8'?>
<codeBook xmlns="ddi:codebook:2_5">
  <docDscr><citation><titlStmt><titl>Empty</titl></titlStmt></citation></docDscr>
</codeBook>
"""

_MISSING_VALUES_XML = """<?xml version='1.0' encoding='UTF-8'?>
<codeBook xmlns="ddi:codebook:2_5">
  <dataDscr>
    <var ID="v1" name="STATUS">
      <labl level="variable">Status</labl>
      <varFormat type="character"/>
      <invalrng><item VALUE="99"/></invalrng>
      <catgry missing="Y"><catValu>99</catValu><labl>Missing</labl></catgry>
      <catgry><catValu>1</catValu><labl>Active</labl></catgry>
    </var>
  </dataDscr>
</codeBook>
"""

_BAD_STAT_XML = """<?xml version='1.0' encoding='UTF-8'?>
<codeBook xmlns="ddi:codebook:2_5">
  <dataDscr>
    <var ID="v1" name="NOTE">
      <varFormat type="character"/>
      <sumStat type="mean">not-a-number</sumStat>
    </var>
  </dataDscr>
</codeBook>
"""


def test_parse_ddi_variables_returns_empty_when_no_data_dscr():
    variables, _matched, total = parse_ddi_variables(_NO_DATA_DSCR_XML)
    assert variables == []
    assert total == 0


def test_parse_ddi_variables_dedupes_missing_values_from_invalrng_and_catgry():
    variables, _matched, total = parse_ddi_variables(_MISSING_VALUES_XML)
    assert total == 1
    assert variables[0]["missing_values"] == ["99"]
    assert variables[0]["value_labels"] == {"99": "Missing", "1": "Active"}


def test_parse_ddi_variables_respects_max_variables_but_reports_total():
    xml = """<?xml version='1.0' encoding='UTF-8'?>
<codeBook xmlns="ddi:codebook:2_5">
  <dataDscr>
    <var ID="v1" name="A"><varFormat type="character"/></var>
    <var ID="v2" name="B"><varFormat type="character"/></var>
    <var ID="v3" name="C"><varFormat type="character"/></var>
  </dataDscr>
</codeBook>
"""
    variables, _matched, total = parse_ddi_variables(xml, max_variables=2)
    assert total == 3
    assert [v["name"] for v in variables] == ["A", "B"]


def test_parse_ddi_variables_drops_summary_stats_when_disabled():
    xml = """<?xml version='1.0' encoding='UTF-8'?>
<codeBook xmlns="ddi:codebook:2_5">
  <dataDscr>
    <var ID="v1" name="AGE"><varFormat type="numeric"/><sumStat type="mean">42</sumStat></var>
  </dataDscr>
</codeBook>
"""
    variables, _, _ = parse_ddi_variables(xml, include_summary_stats=False)
    assert "summary_stats" not in variables[0]


def test_parse_ddi_variables_ignores_non_numeric_summary_stat():
    variables, _, _ = parse_ddi_variables(_BAD_STAT_XML)
    assert variables[0]["summary_stats"]["mean"] == "not-a-number"


_RICH_XML = """<?xml version='1.0' encoding='UTF-8'?>
<codeBook xmlns="ddi:codebook:2_5">
  <dataDscr>
    <varGrp ID="g1" var="v1 v2"><labl>Demographics</labl></varGrp>
    <var ID="v1" name="AGE" intrvl="contin">
      <labl level="variable">Age of respondent</labl>
      <qstn><qstnLit>How old are you?</qstnLit></qstn>
      <notes type="VDC:UNF" subject="Universal Numeric Fingerprint">UNF:6:abc==</notes>
      <notes>Top-coded at 95.</notes>
      <varFormat type="numeric"/>
    </var>
    <var ID="v2" name="REGION" intrvl="discrete">
      <labl level="variable">Geographic region</labl>
      <varFormat type="numeric"/>
      <catgry><catValu>1</catValu><labl>Ontario</labl></catgry>
    </var>
    <var ID="v3" name="WT_FINAL" wgt="wgt">
      <varFormat type="numeric"/>
      <catgry><catValu>1</catValu></catgry>
    </var>
  </dataDscr>
</codeBook>
"""


def test_parse_ddi_variables_extracts_interval_notes_weight_and_groups():
    variables, _, _ = parse_ddi_variables(_RICH_XML)
    age, region, weight = variables
    assert age["interval"] == "contin"
    assert age["notes"] == ["Top-coded at 95."]
    assert age["unf"] == "UNF:6:abc=="
    assert age["groups"] == ["Demographics"]
    assert age["categorical"] is False
    assert region["groups"] == ["Demographics"]
    assert region["categorical"] is True
    assert weight["is_weight"] is True
    assert weight["groups"] == []


def test_parse_ddi_variables_filters_by_name_or_label_then_pages():
    variables, matched, total = parse_ddi_variables(_RICH_XML, name_filter="region")
    assert (matched, total) == (1, 3)
    assert variables[0]["name"] == "REGION"

    variables, matched, _ = parse_ddi_variables(_RICH_XML, name_filter="respondent")
    assert matched == 1 and variables[0]["name"] == "AGE"

    variables, matched, _ = parse_ddi_variables(_RICH_XML, offset=1, max_variables=1)
    assert matched == 3
    assert [v["name"] for v in variables] == ["REGION"]


def test_parse_ddi_variables_without_limit_returns_everything():
    variables, _, total = parse_ddi_variables(_RICH_XML, max_variables=None)
    assert len(variables) == total == 3


@pytest.mark.parametrize("payload", [
    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]><codeBook>&lol;</codeBook>',
    "<codeBook><dataDscr>",
])
def test_parse_ddi_variables_rejects_unsafe_or_malformed_xml(payload):
    with pytest.raises(BorealisError):
        parse_ddi_variables(payload)


def test_documentation_coverage_counts_each_component():
    variables, _, _ = parse_ddi_variables(_RICH_XML)
    assert documentation_coverage(variables) == {
        "variables": 3,
        "labelled": 2,
        "categorical": 2,
        "value_labelled": 1,
        "with_question_text": 1,
    }
