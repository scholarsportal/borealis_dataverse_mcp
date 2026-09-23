"""Regression tests for small parsing/normalization behaviors.

These used to call private helpers on the old top-level `borealis_server`
module (`_delimiter_from_argument`, `_infer_scalar_type`,
`UNIVERSITY_DATAVERSE_MAP`). That module is now a thin backward-compatible
stdio entry point (see borealis_server.py); the logic moved into
`borealis_toolkit.institutions` and inline into
`BorealisService.profile_tabular_file`. These tests exercise the current
equivalents instead of the removed private functions.
"""

from borealis_toolkit.institutions import UNIVERSITY_DATAVERSE_MAP, normalize_institution
from borealis_toolkit.service import BorealisService
from borealis_toolkit.utils import normalize_boolean_query


def test_boolean_normalization_is_word_bounded():
    query = "salmon and trout or char not atlantic Oregon android"
    assert normalize_boolean_query(query) == "salmon AND trout OR char NOT atlantic Oregon android"


def test_corrected_institution_aliases():
    assert UNIVERSITY_DATAVERSE_MAP["athabasca university"] == "athabascau"
    assert UNIVERSITY_DATAVERSE_MAP["university of lethbridge"] == "lethbridge"


def test_normalize_institution_is_case_and_whitespace_insensitive():
    assert normalize_institution("  Athabasca   University ") == "athabascau"
    assert normalize_institution("unknown school") == "unknown school"
    assert normalize_institution(None) is None
    assert normalize_institution("") is None


class FakeDownloadClient:
    def __init__(self, raw: bytes):
        self.raw = raw

    async def download_limited(self, file_id):
        return self.raw, "text/csv", False


async def test_profile_tabular_file_sniffs_delimiter_and_infers_type():
    csv_bytes = b"id,name\n1,north\n2,south\n3,NA\n"
    service = BorealisService(client=FakeDownloadClient(csv_bytes))
    result = await service.profile_tabular_file("1", filename="data.csv")
    columns = {col["name"]: col for col in result.data["columns"]}
    assert result.data["delimiter"] == ","
    assert columns["id"]["inferred_type"] == "number"
    assert columns["name"]["inferred_type"] == "text"
    assert columns["name"]["missing"] == 1


async def test_profile_tabular_file_honors_explicit_tab_delimiter():
    tsv_bytes = b"id\tname\n1\tnorth\n"
    service = BorealisService(client=FakeDownloadClient(tsv_bytes))
    result = await service.profile_tabular_file("1", filename="data.txt", delimiter="tab")
    assert result.data["delimiter"] == "\t"
