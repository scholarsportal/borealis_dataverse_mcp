from borealis_toolkit.ddi import parse_ddi_variables

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
    variables, total = parse_ddi_variables(_NO_DATA_DSCR_XML)
    assert variables == []
    assert total == 0


def test_parse_ddi_variables_dedupes_missing_values_from_invalrng_and_catgry():
    variables, total = parse_ddi_variables(_MISSING_VALUES_XML)
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
    variables, total = parse_ddi_variables(xml, max_variables=2)
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
    variables, _ = parse_ddi_variables(xml, include_summary_stats=False)
    assert "summary_stats" not in variables[0]


def test_parse_ddi_variables_ignores_non_numeric_summary_stat():
    variables, _ = parse_ddi_variables(_BAD_STAT_XML)
    assert variables[0]["summary_stats"]["mean"] == "not-a-number"
