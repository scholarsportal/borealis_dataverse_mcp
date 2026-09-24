from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from . import __version__
from .errors import BorealisError
from .service import BorealisService

app = FastAPI(
    title="Borealis Research Toolkit API",
    version=__version__,
    description="Host-neutral REST interface over Borealis Dataverse research tools.",
)
service = BorealisService()


@app.get("/health")
async def health() -> dict:
    return service.server_status().to_dict()


@app.get("/v1/search")
async def search(
    q: str,
    institution: str | None = None,
    country: str | None = None,
    province: str | None = None,
    city: str | None = None,
    result_type: str = "dataset",
    per_page: int = Query(10, ge=1, le=100),
    start: int = Query(0, ge=0),
    sort: str = "relevance",
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    try:
        result = await service.search_datasets(q, institution=institution, country=country, province=province, city=city, result_type=result_type, per_page=per_page, start=start, sort=sort, date_from=date_from, date_to=date_to)
        return result.to_dict()
    except BorealisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/datasets/metadata")
async def metadata(identifier: str) -> dict:
    try:
        return (await service.get_dataset_metadata(identifier)).to_dict()
    except BorealisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/datasets/files")
async def files(identifier: str, limit: int = 20, offset: int = 0, file_type: str | None = None, version: str = ":latest-published") -> dict:
    try:
        return (await service.list_dataset_files(identifier, limit=limit, offset=offset, file_type=file_type, version=version)).to_dict()
    except BorealisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/files/{file_id}/text")
async def file_text(file_id: str, filename: str = "file.txt", start_line: int = 1, max_lines: int = 100) -> dict:
    try:
        return (await service.get_dataset_file(file_id, filename=filename, start_line=start_line, max_lines=max_lines)).to_dict()
    except (BorealisError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/files/{file_id}/profile")
async def file_profile(file_id: str, filename: str = "table.csv", delimiter: str | None = None, max_rows: int = 100000) -> dict:
    try:
        return (await service.profile_tabular_file(file_id, filename=filename, delimiter=delimiter, max_rows=max_rows)).to_dict()
    except (BorealisError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/files/{file_id}/variables")
async def file_variables(
    file_id: str,
    include_summary_stats: bool = True,
    max_variables: int = 50,
    offset: int = 0,
    name_filter: str | None = None,
) -> dict:
    try:
        return (await service.get_variable_metadata(
            file_id,
            include_summary_stats=include_summary_stats,
            max_variables=max_variables,
            offset=offset,
            name_filter=name_filter,
        )).to_dict()
    except (BorealisError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/datasets/quality")
async def dataset_quality(
    identifier: str,
    include_variable_check: bool = False,
    version: str = ":latest-published",
    max_files_checked: int = 5,
) -> dict:
    try:
        return (await service.assess_metadata_quality(
            identifier,
            include_variable_check=include_variable_check,
            version=version,
            max_files_checked=max_files_checked,
        )).to_dict()
    except (BorealisError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
