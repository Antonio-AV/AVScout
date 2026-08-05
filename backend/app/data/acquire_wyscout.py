"""Acquire the public Wyscout 2017/18 event dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import string
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile


class IntegrityError(RuntimeError):
    """Raised when a downloaded or previously acquired file is invalid."""


@dataclass(frozen=True)
class Asset:
    """Describe a downloaded dataset asset and its local destination.

    Attributes:
        path: Relative path below the acquisition output directory.
        url: Canonical source URL for the asset.
        archive: Whether the asset is a ZIP archive to extract.
        extract_dir: Relative output directory for extracted archive members.
    """

    path: str
    url: str
    archive: bool = False
    extract_dir: str | None = None


ASSETS = (
    Asset(
        "metadata/competitions.json", "https://ndownloader.figshare.com/files/15073685"
    ),
    Asset("metadata/teams.json", "https://ndownloader.figshare.com/files/15073697"),
    Asset("metadata/players.json", "https://ndownloader.figshare.com/files/15073721"),
    Asset(
        "raw/matches.zip",
        "https://ndownloader.figshare.com/files/14464622",
        True,
        "matches",
    ),
    Asset(
        "raw/events.zip",
        "https://ndownloader.figshare.com/files/14464685",
        True,
        "events",
    ),
)

SOURCE = {
    "provider": "Figshare",
    "collection": "Soccer match event dataset",
    "url": "https://figshare.com/collections/Soccer_match_event_dataset/4415000/5",
    "version": "5",
    "citation": (
        "Pappalardo, Luca; Massucco, Emanuele (2019). Soccer match event "
        "dataset. Figshare. https://doi.org/10.6084/m9.figshare.c.4415000.v5"
    ),
}

LICENSE = {
    "name": "CC BY 4.0",
    "url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": (
        "Wyscout public event data, released by Luca Pappalardo and Emanuele "
        "Massucco under CC BY 4.0."
    ),
}

REQUIRED_FILES = tuple(
    f"{league}.json" for league in ("England", "France", "Germany", "Italy", "Spain")
)


def acquire(output_dir: Path = Path("data/wyscout")) -> Path:
    """Download, verify, and extract the five supported domestic leagues.

    Args:
        output_dir: Directory where raw assets, extracted files, and the
            acquisition manifest are stored.

    Returns:
        The path to the written acquisition manifest.

    Raises:
        IntegrityError: If an asset is incomplete, changed, malformed, or
            missing after extraction.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    previous = _read_manifest(manifest_path)
    previous_files = {item["name"]: item for item in previous.get("files", [])}
    records: list[dict[str, Any]] = []

    for asset in ASSETS:
        target = output_dir / asset.path
        previous_record = previous_files.get(asset.path)
        if previous_record is not None and target.exists():
            _verify_existing(target, previous_record)
            record = previous_record
        else:
            record = _download(asset, target)
        records.append(record)

    for asset in ASSETS:
        if asset.archive:
            if asset.extract_dir is None:
                raise IntegrityError(
                    f"archive has no extraction directory: {asset.path}"
                )
            _extract(asset, output_dir / asset.path, output_dir / asset.extract_dir)
    _validate_required_files(output_dir)

    manifest = {
        "schema_version": 1,
        "dataset": "wyscout-public",
        "scope": {
            "season": "2017/2018",
            "competitions": [
                "Premier League",
                "La Liga",
                "Bundesliga",
                "Serie A",
                "Ligue 1",
            ],
        },
        "source": SOURCE,
        "license": LICENSE,
        "files": records,
        "acquired_at": previous.get("acquired_at", _timestamp()),
    }
    _write_json(manifest_path, manifest)
    return manifest_path


def _read_manifest(path: Path) -> dict[str, Any]:
    """Read an existing acquisition manifest.

    Args:
        path: Path to the JSON manifest.

    Returns:
        The decoded manifest object, or an empty dictionary when no manifest
        exists.

    Raises:
        IntegrityError: If the manifest cannot be decoded or is not a JSON
            object.
    """
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"manifest {path} must contain a JSON object")
    return value


def _download(asset: Asset, target: Path) -> dict[str, Any]:
    """Download one asset to a temporary file and verify its integrity.

    Args:
        asset: Dataset asset and canonical source URL to download.
        target: Final path for the downloaded asset.

    Returns:
        Integrity metadata containing the asset name, source URL, byte size,
        SHA-256 digest, MD5 digest, and source ETag.

    Raises:
        IntegrityError: If the response is incomplete, its ETag does not
            match, or the file cannot be written.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.part")
    temporary.unlink(missing_ok=True)
    request = Request(asset.url, headers={"User-Agent": "AVScout data acquisition"})
    byte_count = 0
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    source_etag: str | None = None
    try:
        with urlopen(request) as response, temporary.open("wb") as output:
            expected_length = response.headers.get("Content-Length")
            expected_bytes = int(expected_length) if expected_length else None
            source_etag = response.headers.get("ETag")
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                byte_count += len(chunk)
                sha256.update(chunk)
                md5.update(chunk)
        if expected_bytes is not None and byte_count != expected_bytes:
            raise IntegrityError(
                f"{asset.path}: expected {expected_bytes} bytes, received {byte_count}"
            )
        expected_md5 = _etag_md5(source_etag)
        if expected_md5 is not None and md5.hexdigest() != expected_md5:
            raise IntegrityError(f"{asset.path}: source ETag checksum mismatch")
        os.replace(temporary, target)
    except IntegrityError:
        temporary.unlink(missing_ok=True)
        raise
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise IntegrityError(f"failed to download {asset.path}: {exc}") from exc

    return {
        "name": asset.path,
        "url": asset.url,
        "size_bytes": byte_count,
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "source_etag": source_etag,
    }


def _verify_existing(path: Path, record: dict[str, Any]) -> None:
    """Verify an existing file against manifest size and SHA-256 metadata.

    Args:
        path: Existing downloaded file to inspect.
        record: Manifest record containing the expected size and SHA-256
            digest.

    Returns:
        None.

    Raises:
        IntegrityError: If the manifest metadata is incomplete or the file
            does not match it.
    """
    expected_size = record.get("size_bytes")
    expected_sha256 = record.get("sha256")
    if not isinstance(expected_size, int) or not isinstance(expected_sha256, str):
        raise IntegrityError(f"manifest has incomplete integrity data for {path.name}")
    actual_size = path.stat().st_size
    actual_sha256 = _sha256(path)
    if actual_size != expected_size or actual_sha256 != expected_sha256:
        raise IntegrityError(
            f"existing download failed checksum verification: {path.name}"
        )


def _sha256(path: Path) -> str:
    """Calculate the SHA-256 digest of a file.

    Args:
        path: File whose contents should be hashed.

    Returns:
        The lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _etag_md5(etag: str | None) -> str | None:
    """Extract an MD5 digest from a simple HTTP ETag.

    Args:
        etag: HTTP ETag value, optionally quoted or weakly prefixed.

    Returns:
        The normalized MD5 digest when the ETag is a 32-character hexadecimal
        value, otherwise ``None``.
    """
    if etag is None:
        return None
    value = etag.removeprefix("W/").strip('"')
    if len(value) == 32 and all(character in string.hexdigits for character in value):
        return value.lower()
    return None


def _extract(asset: Asset, archive_path: Path, output_dir: Path) -> None:
    """Safely extract the required domestic files from a ZIP archive.

    Args:
        asset: Archive asset being extracted, used in error messages.
        archive_path: Path to the downloaded ZIP archive.
        output_dir: Directory where the required JSON files are written.

    Returns:
        None.

    Raises:
        IntegrityError: If the archive is invalid or contains an unsafe path.
    """
    try:
        if asset.extract_dir is None:
            raise IntegrityError(f"archive has no extraction directory: {asset.path}")
        with ZipFile(archive_path) as archive:
            root = output_dir.resolve()
            for member in archive.infolist():
                destination = (output_dir / member.filename).resolve()
                if root not in destination.parents and destination != root:
                    raise IntegrityError(
                        f"unsafe path in {asset.path}: {member.filename}"
                    )
            prefix = f"{asset.extract_dir}_"
            expected_members = {f"{prefix}{name}" for name in REQUIRED_FILES}
            output_dir.mkdir(parents=True, exist_ok=True)
            for member in archive.infolist():
                if member.filename in expected_members:
                    output_name = member.filename.removeprefix(prefix)
                    (output_dir / output_name).write_bytes(archive.read(member))
    except BadZipFile as exc:
        raise IntegrityError(f"{asset.path} is not a valid ZIP archive") from exc


def _validate_required_files(output_dir: Path) -> None:
    """Ensure every supported league has matches and events files.

    Args:
        output_dir: Directory containing the extracted Wyscout files.

    Returns:
        None.

    Raises:
        IntegrityError: If one or more required league files are missing.
    """
    missing = [
        f"{directory}/{name}"
        for directory in ("matches", "events")
        for name in REQUIRED_FILES
        if not (output_dir / directory / name).is_file()
    ]
    if missing:
        raise IntegrityError(
            f"Wyscout archive is missing required files: {', '.join(missing)}"
        )


def _timestamp() -> str:
    """Return the current UTC time in ISO 8601 format.

    Returns:
        The current UTC timestamp with a trailing ``Z`` designator.
    """
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    """Write a JSON object atomically to a file.

    Args:
        path: Destination path for the JSON document.
        value: JSON-compatible object to serialize.

    Returns:
        None.
    """
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    """Run the Wyscout acquisition command-line interface.

    Args:
        argv: Optional command-line arguments without the executable name.

    Returns:
        Zero when acquisition succeeds, or one when validation fails.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/wyscout"),
        help="directory for raw files and manifest (default: data/wyscout)",
    )
    args = parser.parse_args(argv)
    try:
        print(acquire(args.output_dir))
    except (IntegrityError, OSError) as exc:
        print(f"acquisition failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
