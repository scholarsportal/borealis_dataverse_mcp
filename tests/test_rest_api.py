import pytest
from fastapi.testclient import TestClient

from borealis_toolkit import rest_api
from borealis_toolkit.errors import BorealisError
from borealis_toolkit.models import Provenance, ToolkitResult


class StubService:
    def __init__(self, *, result=None, error=None):
        self._result = result
        self._error = error

    def _resolve(self):
        if self._error is not None:
            raise self._error
        return self._result

    async def search_datasets(self, *args, **kwargs):
        return self._resolve()

    async def get_dataset_metadata(self, *args, **kwargs):
        return self._resolve()

    async def list_dataset_files(self, *args, **kwargs):
        return self._resolve()

    async def get_dataset_file(self, *args, **kwargs):
        return self._resolve()

    async def profile_tabular_file(self, *args, **kwargs):
        return self._resolve()

    async def get_variable_metadata(self, *args, **kwargs):
        return self._resolve()

    async def assess_metadata_quality(self, *args, **kwargs):
        return self._resolve()

    def server_status(self):
        return self._resolve()


@pytest.fixture
def client(monkeypatch):
    return TestClient(rest_api.app)


def _ok_result(data):
    return ToolkitResult(data, Provenance("GET /api/test", "2026-01-01T00:00:00+00:00", False, {}))


def test_health_returns_server_status(client, monkeypatch):
    monkeypatch.setattr(rest_api, "service", StubService(result=_ok_result({"name": "Borealis Research Toolkit"})))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Borealis Research Toolkit"


def test_search_returns_200_with_structured_payload(client, monkeypatch):
    monkeypatch.setattr(rest_api, "service", StubService(result=_ok_result({"results": []})))
    response = client.get("/v1/search", params={"q": "bees"})
    assert response.status_code == 200
    assert response.json()["data"]["results"] == []


def test_search_maps_borealis_error_to_502(client, monkeypatch):
    monkeypatch.setattr(rest_api, "service", StubService(error=BorealisError("upstream failed")))
    response = client.get("/v1/search", params={"q": "bees"})
    assert response.status_code == 502
    assert response.json()["detail"] == "upstream failed"


def test_file_text_maps_borealis_error_to_400(client, monkeypatch):
    monkeypatch.setattr(rest_api, "service", StubService(error=BorealisError("not a text file")))
    response = client.get("/v1/files/1/text")
    assert response.status_code == 400
    assert response.json()["detail"] == "not a text file"


def test_file_text_maps_value_error_to_400(client, monkeypatch):
    monkeypatch.setattr(rest_api, "service", StubService(error=ValueError("no header row")))
    response = client.get("/v1/files/1/profile")
    assert response.status_code == 400


def test_dataset_quality_returns_200(client, monkeypatch):
    monkeypatch.setattr(rest_api, "service", StubService(result=_ok_result({"score": 80, "grade": "B"})))
    response = client.get("/v1/datasets/quality", params={"identifier": "doi:10.5683/SP3/EXAMPLE"})
    assert response.status_code == 200
    assert response.json()["data"]["grade"] == "B"
