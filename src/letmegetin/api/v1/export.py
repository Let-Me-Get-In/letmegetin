"""Read-only serving of the ODbL export files the operator CLI writes (D-11)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from letmegetin.api.deps import public_rate_limit
from letmegetin.config import settings

router = APIRouter(prefix="/api/v1", tags=["export"], dependencies=[Depends(public_rate_limit)])

_NOT_AVAILABLE = "Export not available"
# The directory also holds `latest.json.lock` and transient `.<name>.zip.tmp` files;
# no partner ever downloads those.
_NEVER_SERVED = (".lock", ".tmp")


@router.get(
    "/export/latest.json",
    summary="Latest ODbL export index",
    description=(
        "The index written by `letmegetin-admin export odbl`: current snapshot, delta watermark, "
        "retention floor and the deltas available. The API serves the file as written and never "
        "generates or rewrites it. Returns 404 when no export exists — including on a deployment "
        "whose export volume is not provisioned (the directory has no default content)."
    ),
)
async def get_export_latest() -> JSONResponse:
    """Serve the CLI-written export index."""
    try:
        payload = json.loads((settings.export_dir / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail=_NOT_AVAILABLE) from None
    return JSONResponse(payload, headers={"Cache-Control": "public, max-age=300"})


@router.get(
    "/export/{name}.zip",
    summary="Download an ODbL export archive",
    response_class=FileResponse,
    responses={200: {"description": "The archive.", "content": {"application/zip": {}}}},
    description=(
        "A snapshot, delta or catch-up archive from the export directory. The name must be a "
        "plain file name: a separator, `..`, a dotfile, the lock or a temp file is refused with "
        "404 before the filesystem is touched, and 404 is also the answer for an archive that "
        "does not exist yet."
    ),
)
async def get_export_zip(name: str) -> FileResponse:
    """Serve one export archive; the name is validated before any filesystem access (T-14-07)."""
    filename = f"{name}.zip"
    if not _is_servable(filename):
        raise HTTPException(status_code=404, detail=_NOT_AVAILABLE)
    path = (settings.export_dir / filename).resolve()
    if not path.is_relative_to(settings.export_dir.resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail=_NOT_AVAILABLE)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=filename,
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _is_servable(filename: str) -> bool:
    """A served name is a plain `.zip` file name, never a path, a lock or a temp file."""
    return (
        filename.endswith(".zip")
        and filename.isprintable()  # a NUL byte would reach Path.resolve() and raise
        and not filename.startswith(".")
        and "/" not in filename
        and "\\" not in filename
        and ".." not in filename
        and not any(fragment in filename for fragment in _NEVER_SERVED)
    )
