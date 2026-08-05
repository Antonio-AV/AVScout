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
    """Minimal response object used to exercise the downloader boundary."""

    def __init__(
        self,
        content: bytes,
        content_length: int | None = None,
        etag: str | None = None,
    ) -> None:
        """Create a readable response with optional integrity headers.

        Args:
            content: Bytes returned by the fake response.
            content_length: Optional HTTP content length header.
            etag: Optional HTTP ETag header.

        Returns:
            None.
        """
        self._content = io.BytesIO(content)
        self.headers = {
            **({"Content-Length": str(content_length)} if content_length else {}),
            **({"ETag": etag} if etag else {}),
        }

    def __enter__(self) -> FakeResponse:
        """Return this response as a context manager value.

        Returns:
            This fake response instance.
        """
        return self

    def __exit__(self, *_args: Any) -> None:
        """Close the in-memory response body.

        Args:
            *_args: Context manager exception details supplied by Python.

        Returns:
            None.
        """
        self._content.close()

    def read(self, size: int = -1) -> bytes:
        """Read bytes from the fake response body.

        Args:
            size: Maximum number of bytes to read, or ``-1`` for all bytes.

        Returns:
            The next bytes from the response body.
        """
        return self._content.read(size)


def zip_bytes(*names: str) -> bytes:
    """Create an in-memory ZIP archive containing named JSON fixtures.

    Args:
        *names: Archive member names to create.

    Returns:
        The serialized ZIP archive bytes.
    """
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        for name in names:
            archive.writestr(name, "[]")
    return output.getvalue()


def test_acquire_downloads_assets_extracts_leagues_and_writes_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Acquire all assets and write the expected manifest and league files.

    Args:
        tmp_path: Temporary output directory supplied by pytest.
        monkeypatch: Pytest patching fixture for the fake downloader.

    Returns:
        None.
    """
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
        """Return deterministic bytes for a requested asset URL.

        Args:
            request: URL request passed by the acquisition command.

        Returns:
            A fake response containing the requested fixture bytes.
        """
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
    assert (tmp_path / "metadata/competitions.json").exists()
    assert (tmp_path / "metadata/players.json").exists()
    assert (tmp_path / "metadata/teams.json").exists()
    assert (tmp_path / "raw/matches.zip").exists()
    assert (tmp_path / "raw/events.zip").exists()
    for league in ("England", "France", "Germany", "Italy", "Spain"):
        assert (tmp_path / f"matches/{league}.json").exists()
        assert (tmp_path / f"events/{league}.json").exists()


def test_acquire_rejects_a_changed_existing_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a previously acquired file after its contents change.

    Args:
        tmp_path: Temporary output directory supplied by pytest.
        monkeypatch: Pytest patching fixture for the fake downloader.

    Returns:
        None.
    """
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
        """Return deterministic bytes for a requested asset URL.

        Args:
            request: URL request passed by the acquisition command.

        Returns:
            A fake response containing the requested fixture bytes.
        """
        return FakeResponse(archives.get(request.full_url, b"{}"))

    monkeypatch.setattr("app.data.acquire_wyscout.urlopen", fake_urlopen)
    assert main(["--output-dir", str(tmp_path)]) == 0
    (tmp_path / "metadata/competitions.json").write_bytes(b"changed")

    assert main(["--output-dir", str(tmp_path)]) == 1


def test_acquire_rejects_an_archive_missing_a_previous_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a new archive instead of accepting stale extracted output.

    Args:
        tmp_path: Temporary output directory supplied by pytest.
        monkeypatch: Pytest patching fixture for the fake downloader.

    Returns:
        None.
    """
    events_url = "https://ndownloader.figshare.com/files/14464685"
    archives = {
        "https://ndownloader.figshare.com/files/14464622": zip_bytes(
            *(
                f"matches_{league}.json"
                for league in ("England", "France", "Germany", "Italy", "Spain")
            )
        ),
        events_url: zip_bytes(
            *(
                f"events_{league}.json"
                for league in ("England", "France", "Germany", "Italy", "Spain")
            )
        ),
    }

    def fake_urlopen(request: Any) -> FakeResponse:
        """Return the currently configured archive fixture.

        Args:
            request: URL request passed by the acquisition command.

        Returns:
            A fake response containing the requested fixture bytes.
        """
        return FakeResponse(archives.get(request.full_url, b"{}"))

    monkeypatch.setattr("app.data.acquire_wyscout.urlopen", fake_urlopen)
    assert main(["--output-dir", str(tmp_path)]) == 0
    (tmp_path / "raw/events.zip").unlink()
    archives[events_url] = zip_bytes(
        "events_England.json",
        "events_France.json",
        "events_Germany.json",
        "events_Italy.json",
    )

    assert main(["--output-dir", str(tmp_path)]) == 1
    assert (tmp_path / "events/Spain.json").exists()


def test_acquire_rejects_a_truncated_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a response whose body is shorter than its content length.

    Args:
        tmp_path: Temporary output directory supplied by pytest.
        monkeypatch: Pytest patching fixture for the fake downloader.

    Returns:
        None.
    """

    def fake_urlopen(_request: Any) -> FakeResponse:
        """Return a deliberately truncated response.

        Args:
            _request: URL request ignored by this deterministic fixture.

        Returns:
            A response whose declared length exceeds its body.
        """
        return FakeResponse(b"{}", content_length=3)

    monkeypatch.setattr("app.data.acquire_wyscout.urlopen", fake_urlopen)

    assert main(["--output-dir", str(tmp_path)]) == 1

    assert not (tmp_path / "competitions.json").exists()
    assert not (tmp_path / "manifest.json").exists()


def test_acquire_rejects_a_source_checksum_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a response whose bytes do not match its source ETag.

    Args:
        tmp_path: Temporary output directory supplied by pytest.
        monkeypatch: Pytest patching fixture for the fake downloader.

    Returns:
        None.
    """

    def fake_urlopen(_request: Any) -> FakeResponse:
        """Return bytes with an intentionally incorrect source ETag.

        Args:
            _request: URL request ignored by this deterministic fixture.

        Returns:
            A response whose body does not match its ETag.
        """
        return FakeResponse(b"{}", etag='"00000000000000000000000000000000"')

    monkeypatch.setattr("app.data.acquire_wyscout.urlopen", fake_urlopen)

    assert main(["--output-dir", str(tmp_path)]) == 1
    assert not (tmp_path / "competitions.json").exists()
