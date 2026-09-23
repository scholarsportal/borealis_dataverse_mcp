import httpx
import pytest
import respx

from borealis_toolkit.client import BorealisClient
from borealis_toolkit.config import Settings
from borealis_toolkit.errors import (
    BorealisAccessError,
    BorealisError,
    BorealisFileTooLargeError,
    BorealisNotFoundError,
    BorealisUnsupportedFileError,
)


def make_client(**overrides) -> BorealisClient:
    settings = Settings(api_base_url="https://example.test/api", **overrides)
    return BorealisClient(settings=settings)


@respx.mock
async def test_request_json_returns_payload_on_success():
    respx.get("https://example.test/api/search").mock(
        return_value=httpx.Response(200, json={"status": "OK", "data": {"total_count": 0, "items": []}})
    )
    client = make_client()
    payload, used_auth = await client.request_json("GET", "search")
    assert payload["data"]["total_count"] == 0
    assert used_auth is False


@respx.mock
async def test_request_json_raises_not_found_on_404():
    respx.get("https://example.test/api/datasets/999/metadata").mock(return_value=httpx.Response(404))
    client = make_client()
    with pytest.raises(BorealisNotFoundError):
        await client.request_json("GET", "datasets/999/metadata")


@respx.mock
async def test_request_json_raises_access_error_on_403():
    respx.get("https://example.test/api/restricted").mock(return_value=httpx.Response(403))
    client = make_client()
    with pytest.raises(BorealisAccessError):
        await client.request_json("GET", "restricted")


@respx.mock
async def test_request_json_retries_without_auth_after_401():
    route = respx.get("https://example.test/api/search")
    route.side_effect = [
        httpx.Response(401),
        httpx.Response(200, json={"status": "OK", "data": {}}),
    ]
    client = make_client(api_key="a-fairly-long-fake-key")
    payload, used_auth = await client.request_json("GET", "search")
    assert payload == {"status": "OK", "data": {}}
    assert used_auth is False
    assert route.call_count == 2


@respx.mock
async def test_request_json_raises_on_non_ok_status_field():
    respx.get("https://example.test/api/search").mock(
        return_value=httpx.Response(200, json={"status": "ERROR", "message": "bad request"})
    )
    client = make_client()
    with pytest.raises(BorealisError):
        await client.request_json("GET", "search")


@respx.mock
async def test_request_text_raises_unsupported_file_on_400():
    respx.get("https://example.test/api/access/datafile/1/metadata/ddi").mock(
        return_value=httpx.Response(400, text="not tabular")
    )
    client = make_client()
    with pytest.raises(BorealisUnsupportedFileError):
        await client.request_text("GET", "access/datafile/1/metadata/ddi")


@respx.mock
async def test_download_limited_returns_bytes_and_content_type():
    respx.get("https://example.test/api/access/datafile/1").mock(
        return_value=httpx.Response(200, content=b"hello world", headers={"content-type": "text/plain"})
    )
    client = make_client()
    content, content_type, _used_auth = await client.download_limited("1")
    assert content == b"hello world"
    assert content_type == "text/plain"


@respx.mock
async def test_download_limited_raises_when_over_max_bytes():
    respx.get("https://example.test/api/access/datafile/1").mock(return_value=httpx.Response(200, content=b"x" * 100))
    client = make_client(max_file_bytes=10)
    with pytest.raises(BorealisFileTooLargeError):
        await client.download_limited("1")
