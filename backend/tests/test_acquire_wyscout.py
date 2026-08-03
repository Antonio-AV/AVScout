from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from app.data.acquire_wyscout import main


class FakeResponse:
    def __init__(
        self,
        content: bytes,
        content_length: int | None = None,
        etag: str | None = None,
    ) -> None:
        self._content = io.BytesIO(content)
        self.headers = {
            **({"Content-Length": str(content_length)} if content_length else {}),
            **({"ETag": etag} if etag else {}),
        }

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: Any) -> None:
        self._content.close()

    def read(self, size: int = -1) -> bytes:
        return self._content.read(size)


def zip_bytes(*names: str) -> bytes:
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        for name in names:
            archive.writestr(name, "[]")
    return output.getvalue()


def test_acquire_downloads_assets_extracts_leagues_and_writes_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archives = {
        "https://ndownloader.figshare.com/files/14464622": zip_bytes(
            "matches_England.json",
            "matches_France.json",
            "matches_Germany.json",
            "matches_Italy.json",
            "matches_Spain.json",
        ),
        "https://ndownloader.figshare.com/files/14464685": zip_bytes(
            "events_England.json",
            "events_France.json",
            "events_Germany.json",
            "events_Italy.json",
            "events_Spain.json",
        ),
    }
    downloaded: list[str] = []

    def fake_urlopen(request: Any) -> FakeResponse:
        url = request.full_url
        downloaded.append(url)
        return FakeResponse(archives.get(url, b"{}"))

    monkeypatch.setattr("app.data.acquire_wyscout.urlopen", fake_urlopen)

    assert main(["--output-dir", str(tmp_path)]) == 0
    manifest_path = tmp_path / "manifest.json"

    manifest = json.loads(manifest_path.read_text())
    assert len(downloaded) == 5
    assert manifest["source"]["version"] == "5"
    assert manifest["license"]["name"] == "CC BY 4.0"
    assert len(manifest["files"]) == 5
    assert manifest["files"][0]["sha256"] == hashlib.sha256(b"{}").hexdigest()
    for league in ("England", "France", "Germany", "Italy", "Spain"):
        assert (tmp_path / f"matches_{league}.json").exists()
        assert (tmp_path / f"events_{league}.json").exists()


def test_acquire_rejects_a_changed_existing_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archives = {
        "https://ndownloader.figshare.com/files/14464622": zip_bytes(
            *(
                f"matches_{league}.json"
                for league in ("England", "France", "Germany", "Italy", "Spain")
            )
        ),
        "https://ndownloader.figshare.com/files/14464685": zip_bytes(
            *(
                f"events_{league}.json"
                for league in ("England", "France", "Germany", "Italy", "Spain")
            )
        ),
    }

    def fake_urlopen(request: Any) -> FakeResponse:
        return FakeResponse(archives.get(request.full_url, b"{}"))

    monkeypatch.setattr("app.data.acquire_wyscout.urlopen", fake_urlopen)
    assert main(["--output-dir", str(tmp_path)]) == 0
    (tmp_path / "competitions.json").write_bytes(b"changed")

    assert main(["--output-dir", str(tmp_path)]) == 1


def test_acquire_rejects_a_truncated_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.data.acquire_wyscout.urlopen",
        lambda _request: FakeResponse(b"{}", content_length=3),
    )

    assert main(["--output-dir", str(tmp_path)]) == 1

    assert not (tmp_path / "competitions.json").exists()
    assert not (tmp_path / "manifest.json").exists()


def test_acquire_rejects_a_source_checksum_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.data.acquire_wyscout.urlopen",
        lambda _request: FakeResponse(b"{}", etag='"00000000000000000000000000000000"'),
    )

    assert main(["--output-dir", str(tmp_path)]) == 1
    assert not (tmp_path / "competitions.json").exists()
