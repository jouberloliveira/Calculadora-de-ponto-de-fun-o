"""Tests for archive extraction security guards."""

from __future__ import annotations

import io
import zipfile

import pytest

from app.ingest import (
    ZipBombError,
    ZipSlipError,
    extract_archive,
    ingest_uploads,
)


def _build_zip(entries: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return buf.getvalue()


def _build_zip_with_traversal_path() -> bytes:
    """Write a ZIP whose member name escapes the extraction root.

    zipfile.writestr will not let us inject ``../`` directly via the public
    API because it normalises names. We craft a ZipInfo manually so we keep
    the offending path verbatim.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo(filename="../escape.txt")
        zf.writestr(info, b"pwned")
    return buf.getvalue()


def test_extract_archive_rejects_zip_slip() -> None:
    payload = _build_zip_with_traversal_path()
    with pytest.raises(ZipSlipError):
        extract_archive(
            payload,
            max_decompressed_bytes=1_000_000,
            max_files=100,
            max_text_chars_per_file=10_000,
        )


def test_extract_archive_rejects_absolute_path() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo(filename="/etc/passwd.txt")
        zf.writestr(info, b"root:x:0:0")
    with pytest.raises(ZipSlipError):
        extract_archive(
            buf.getvalue(),
            max_decompressed_bytes=1_000_000,
            max_files=100,
            max_text_chars_per_file=10_000,
        )


def test_extract_archive_rejects_zip_bomb_by_size() -> None:
    # A single large file declared bigger than the cap.
    big = b"A" * (2 * 1024 * 1024)
    payload = _build_zip([("big.txt", big)])
    with pytest.raises(ZipBombError):
        extract_archive(
            payload,
            max_decompressed_bytes=1 * 1024 * 1024,  # 1 MB cap, file is 2 MB
            max_files=100,
            max_text_chars_per_file=10_000,
        )


def test_extract_archive_rejects_zip_bomb_by_count() -> None:
    entries = [(f"f{i}.txt", b"x") for i in range(50)]
    payload = _build_zip(entries)
    with pytest.raises(ZipBombError):
        extract_archive(
            payload,
            max_decompressed_bytes=1_000_000,
            max_files=10,
            max_text_chars_per_file=10_000,
        )


def test_extract_archive_happy_path_returns_text_files() -> None:
    payload = _build_zip(
        [
            ("src/app.py", b"print('hi')\n"),
            ("README.md", b"# Title\n"),
            ("binary.bin", b"\x00\x01\x02"),  # skipped (not allowlisted)
        ]
    )
    files = extract_archive(
        payload,
        max_decompressed_bytes=1_000_000,
        max_files=100,
        max_text_chars_per_file=10_000,
    )
    names = {f.name for f in files}
    assert names == {"src/app.py", "README.md"}


def test_ingest_uploads_passes_through_plain_files() -> None:
    files = ingest_uploads(
        [("hello.py", b"print('hi')\n"), ("ignored.exe", b"\x00")],
        max_decompressed_bytes=1_000_000,
        max_files=100,
        max_text_chars_per_file=10_000,
    )
    assert [f.name for f in files] == ["hello.py"]
