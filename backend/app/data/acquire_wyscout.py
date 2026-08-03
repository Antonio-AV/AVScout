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
    filename: str
    url: str
    archive: bool = False


ASSETS = (
    Asset("competitions.json", "https://ndownloader.figshare.com/files/15073685"),
    Asset("teams.json", "https://ndownloader.figshare.com/files/15073697"),
    Asset("players.json", "https://ndownloader.figshare.com/files/15073721"),
    Asset("matches.zip", "https://ndownloader.figshare.com/files/14464622", True),
    Asset("events.zip", "https://ndownloader.figshare.com/files/14464685", True),
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
    f"{kind}_{league}.json"
    for kind in ("matches", "events")
    for league in ("England", "France", "Germany", "Italy", "Spain")
)


def acquire(output_dir: Path = Path("data/wyscout")) -> Path:
    """Download, verify, and extract the five supported domestic leagues."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    previous = _read_manifest(manifest_path)
    previous_files = {item["name"]: item for item in previous.get("files", [])}
    records: list[dict[str, Any]] = []

    for asset in ASSETS:
        target = output_dir / asset.filename
        previous_record = previous_files.get(asset.filename)
        if previous_record is not None and target.exists():
            _verify_existing(target, previous_record)
            record = previous_record
        else:
            record = _download(asset, target)
        records.append(record)

    for asset in ASSETS:
        if asset.archive:
            _extract(asset, output_dir / asset.filename, output_dir)
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
                f"{asset.filename}: expected {expected_bytes} bytes, received "
                f"{byte_count}"
            )
        expected_md5 = _etag_md5(source_etag)
        if expected_md5 is not None and md5.hexdigest() != expected_md5:
            raise IntegrityError(f"{asset.filename}: source ETag checksum mismatch")
        os.replace(temporary, target)
    except IntegrityError:
        temporary.unlink(missing_ok=True)
        raise
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise IntegrityError(f"failed to download {asset.filename}: {exc}") from exc

    return {
        "name": asset.filename,
        "url": asset.url,
        "size_bytes": byte_count,
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "source_etag": source_etag,
    }


def _verify_existing(path: Path, record: dict[str, Any]) -> None:
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
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _etag_md5(etag: str | None) -> str | None:
    if etag is None:
        return None
    value = etag.removeprefix("W/").strip('"')
    if len(value) == 32 and all(character in string.hexdigits for character in value):
        return value.lower()
    return None


def _extract(asset: Asset, archive_path: Path, output_dir: Path) -> None:
    try:
        with ZipFile(archive_path) as archive:
            root = output_dir.resolve()
            for member in archive.infolist():
                destination = (output_dir / member.filename).resolve()
                if root not in destination.parents and destination != root:
                    raise IntegrityError(
                        f"unsafe path in {asset.filename}: {member.filename}"
                    )
            for member in archive.infolist():
                if member.filename in REQUIRED_FILES:
                    archive.extract(member, output_dir)
    except BadZipFile as exc:
        raise IntegrityError(f"{asset.filename} is not a valid ZIP archive") from exc


def _validate_required_files(output_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (output_dir / name).is_file()]
    if missing:
        raise IntegrityError(
            f"Wyscout archive is missing required files: {', '.join(missing)}"
        )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
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
