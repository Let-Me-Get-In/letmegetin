"""The read-only ODbL export routes: serve, 404, stay inside the directory, stay rate-limited."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from letmegetin.api.v1.export import _is_servable
from letmegetin.config import settings
from letmegetin.main import app

_MARKER = "TOP-SECRET-MARKER-a71f"
_INDEX = {"snapshot": {"name": "export-20261114-full.zip", "seq": 12}, "watermark": 12}
_ZIP = b"PK\x03\x04not-really-a-zip-but-opaque"


@pytest.fixture
def export_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A served directory holding one index and one archive; a secret sits beside it."""
    directory = tmp_path / "export"
    directory.mkdir()
    (directory / "latest.json").write_text(json.dumps(_INDEX), encoding="utf-8")
    (directory / "export-20261114-full.zip").write_bytes(_ZIP)
    (tmp_path / "secret.txt").write_text(_MARKER, encoding="utf-8")
    monkeypatch.setattr(settings, "export_dir", directory)
    return directory


def test_latest_json_serves_the_index_the_cli_wrote(client: TestClient, export_dir: Path) -> None:
    response = client.get("/api/v1/export/latest.json")

    assert response.status_code == 200
    assert response.json() == _INDEX
    assert response.headers["cache-control"] == "public, max-age=300"


def test_latest_json_is_404_before_the_first_export(client: TestClient, export_dir: Path) -> None:
    (export_dir / "latest.json").unlink()

    response = client.get("/api/v1/export/latest.json")

    assert response.status_code == 404
    assert response.json()["detail"] == "Export not available"


def test_latest_json_is_404_when_the_index_is_unreadable(
    client: TestClient, export_dir: Path
) -> None:
    (export_dir / "latest.json").write_text("{not json", encoding="utf-8")

    response = client.get("/api/v1/export/latest.json")

    assert response.status_code == 404


def test_zip_serves_the_archive_with_the_zip_media_type(
    client: TestClient, export_dir: Path
) -> None:
    response = client.get("/api/v1/export/export-20261114-full.zip")

    assert response.status_code == 200
    assert response.content == _ZIP
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "public, max-age=3600"


def test_zip_is_404_for_an_archive_that_does_not_exist(
    client: TestClient, export_dir: Path
) -> None:
    response = client.get("/api/v1/export/delta-20261114.zip")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/export/../secret.txt",
        "/api/v1/export/..%2Fsecret.txt",
        "/api/v1/export/%2e%2e%2Fsecret.txt",
        "/api/v1/export/%2Fetc%2Fpasswd.zip",
        "/api/v1/export/a/b.zip",
        "/api/v1/export/x.txt",
        "/api/v1/export/..",
        "/api/v1/export/latest.json.lock",
        "/api/v1/export/.export-20261114-full.zip.tmp",
    ],
    ids=[
        "parent-segment",
        "encoded-parent-slash",
        "encoded-dot-dot",
        "encoded-absolute",
        "nested-segment",
        "not-a-zip",
        "dot-dot",
        "lock-file",
        "temp-file",
    ],
)
def test_a_traversal_name_never_escapes_the_export_directory(
    client: TestClient, export_dir: Path, path: str
) -> None:
    response = client.get(path)

    assert response.status_code in (400, 404, 422), response.status_code
    assert _MARKER not in response.text


def test_a_symlink_out_of_the_directory_is_not_served(
    client: TestClient, export_dir: Path, tmp_path: Path
) -> None:
    """The resolved path must stay under export_dir, so a planted symlink cannot leak."""
    (export_dir / "leak.zip").symlink_to(tmp_path / "secret.txt")

    response = client.get("/api/v1/export/leak.zip")

    assert response.status_code == 404
    assert _MARKER not in response.text


@pytest.mark.parametrize(
    ("name", "servable"),
    [
        ("export-20261114-full.zip", True),
        ("delta-20261114.zip", True),
        ("../secret.txt", False),
        ("..\\secret.txt", False),
        ("/etc/passwd.zip", False),
        ("a/b.zip", False),
        ("secret.txt", False),
        ("latest.json.lock", False),
        (".export-1.zip.tmp", False),
    ],
)
def test_only_a_plain_zip_name_is_servable(name: str, servable: bool) -> None:
    assert _is_servable(name) is servable


@pytest.mark.parametrize(
    "path", ["/api/v1/export/latest.json", "/api/v1/export/export-20261114-full.zip"]
)
def test_both_export_routes_stay_under_the_anonymous_rate_limit(
    client: TestClient, export_dir: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr(settings, "rate_limit_default_rpm", 1)

    assert client.get(path).status_code == 200
    assert client.get(path).status_code == 429


def test_openapi_documents_both_export_routes() -> None:
    schema = app.openapi()

    for path in ("/api/v1/export/latest.json", "/api/v1/export/{name}.zip"):
        operation = schema["paths"][path]["get"]
        assert operation["summary"]
        assert operation["description"]
        assert operation["tags"] == ["export"]

    export_tag = next(tag for tag in schema["tags"] if tag["name"] == "export")
    assert "ODbL" in export_tag["description"]
