"""File ingestion with hardened archive extraction.

Guards against zip slip and zip bombs:
* path traversal — resolve each member's real path under the extraction root
  and reject anything that escapes the root.
* decompression amplification — abort once total decompressed bytes or file
  count crosses configured caps, before writing the offending member.
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

from pdfminer.high_level import extract_text as pdf_extract_text

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go",
    ".md", ".txt", ".json", ".yml", ".yaml", ".toml",
    ".rb", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".html", ".css", ".scss", ".sh", ".sql",
}
PDF_EXTENSIONS = {".pdf"}
ARCHIVE_EXTENSIONS = {".zip"}
ACCEPTED_EXTENSIONS = TEXT_EXTENSIONS | PDF_EXTENSIONS | ARCHIVE_EXTENSIONS


class IngestError(Exception):
    """Base ingestion error."""


class ZipSlipError(IngestError):
    """Archive member resolved outside extraction root."""


class ZipBombError(IngestError):
    """Archive exceeds decompressed-size or file-count caps."""


@dataclass(frozen=True)
class ExtractedFile:
    name: str          # relative path (display)
    content: str       # text content
    bytes_in: int      # raw text bytes
    source: str        # original upload filename or "<inline>"


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.relative_to(base)
    except ValueError:
        return False
    return True


def extract_archive(
    archive_bytes: bytes,
    *,
    max_decompressed_bytes: int,
    max_files: int,
    max_text_chars_per_file: int,
    source_name: str = "<archive>",
) -> list[ExtractedFile]:
    """Extract a zip archive into a temp dir with zip slip / bomb guards.

    Returns text-decodable files only. Binary / non-allowlisted members are
    skipped silently. PDFs nested in the archive are parsed with pdfminer.
    """
    out: list[ExtractedFile] = []
    total_bytes = 0

    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        try:
            zf = zipfile.ZipFile(io.BytesIO(archive_bytes))
        except zipfile.BadZipFile as exc:
            raise IngestError(f"Invalid zip archive: {source_name}") from exc

        with zf:
            members = zf.infolist()
            if len(members) > max_files:
                raise ZipBombError(
                    f"Archive contains {len(members)} entries (cap {max_files})"
                )

            for info in members:
                if info.is_dir():
                    continue

                # Reject absolute paths or paths with traversal segments up front.
                if info.filename.startswith(("/", "\\")) or ".." in Path(info.filename).parts:
                    raise ZipSlipError(f"Unsafe archive member path: {info.filename}")

                target = (root / info.filename).resolve()
                if not _is_within(root, target):
                    raise ZipSlipError(
                        f"Archive member escapes root: {info.filename}"
                    )

                projected = total_bytes + info.file_size
                if projected > max_decompressed_bytes:
                    raise ZipBombError(
                        "Decompressed size cap exceeded "
                        f"({projected} > {max_decompressed_bytes})"
                    )

                ext = Path(info.filename).suffix.lower()
                if ext not in (TEXT_EXTENSIONS | PDF_EXTENSIONS):
                    # Skip silently — only count toward decompressed budget if we
                    # actually read it. We still update total_bytes by file_size
                    # to keep the bomb guard honest about claimed sizes.
                    total_bytes = projected
                    continue

                try:
                    raw = zf.read(info)
                except zipfile.BadZipFile as exc:
                    raise IngestError(
                        f"Corrupt archive member: {info.filename}"
                    ) from exc

                # zf.read returns actual bytes; re-check against the cap.
                total_bytes += len(raw)
                if total_bytes > max_decompressed_bytes:
                    raise ZipBombError(
                        "Decompressed size cap exceeded after read "
                        f"({total_bytes} > {max_decompressed_bytes})"
                    )

                content = _bytes_to_text(
                    raw, ext, max_text_chars_per_file, info.filename
                )
                if content is None:
                    continue

                out.append(
                    ExtractedFile(
                        name=info.filename,
                        content=content,
                        bytes_in=len(raw),
                        source=source_name,
                    )
                )
    return out


def _bytes_to_text(
    raw: bytes, ext: str, max_chars: int, name: str
) -> str | None:
    if ext in PDF_EXTENSIONS:
        try:
            text = pdf_extract_text(io.BytesIO(raw)) or ""
        except Exception as exc:  # pdfminer raises broad exceptions
            logger.warning("PDF parse failed for %s: %s", name, exc)
            return None
        return text[:max_chars]

    if ext in TEXT_EXTENSIONS:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
            except UnicodeDecodeError:
                return None
        return text[:max_chars]

    return None


def ingest_uploads(
    uploads: Iterable[tuple[str, bytes]],
    *,
    max_decompressed_bytes: int,
    max_files: int,
    max_text_chars_per_file: int,
) -> list[ExtractedFile]:
    """Convert raw uploads into a list of text-bearing ExtractedFile.

    ``uploads`` is an iterable of (filename, bytes). Zip archives are
    expanded; PDFs and source files are read directly.
    """
    out: list[ExtractedFile] = []
    for filename, raw in uploads:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ACCEPTED_EXTENSIONS:
            continue

        if ext in ARCHIVE_EXTENSIONS:
            out.extend(
                extract_archive(
                    raw,
                    max_decompressed_bytes=max_decompressed_bytes,
                    max_files=max_files,
                    max_text_chars_per_file=max_text_chars_per_file,
                    source_name=filename,
                )
            )
            continue

        content = _bytes_to_text(raw, ext, max_text_chars_per_file, filename)
        if content is None:
            continue
        out.append(
            ExtractedFile(
                name=filename,
                content=content,
                bytes_in=len(raw),
                source=filename,
            )
        )
    return out
