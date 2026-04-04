from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import subprocess
import tempfile


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".log",
    ".xml",
    ".html",
    ".htm",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}
MIN_PDF_TEXT_CHARS = 40
MAX_OCR_PAGES = 12
_MOJIBAKE_MARKERS: tuple[str, ...] = ("Đ", "Ń", "Â", "Ã", "Ð", "Ñ", "�")


def _clean_extracted_text(value: str) -> str:
    text = (value or "").replace("\x00", " ")
    text = _repair_mojibake_text(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _looks_mojibake(value: str) -> bool:
    text = str(value or "")
    if not text:
        return False
    markers = sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
    return markers >= 3


def _text_quality_score(value: str) -> float:
    text = str(value or "")
    if not text:
        return float("-inf")
    cyrillic_count = len(re.findall(r"[А-Яа-яІіЇїЄєҐґ]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    marker_count = sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
    replacement_count = text.count("�")
    # Higher is better: prefer readable Cyrillic/Latin and penalize mojibake markers.
    return float(
        cyrillic_count * 3 + latin_count * 2 - marker_count * 5 - replacement_count * 8
    )


def _select_best_text_candidate(candidates: list[str]) -> str:
    cleaned_candidates = [
        _clean_extracted_text(item)
        for item in candidates
        if _clean_extracted_text(item)
    ]
    if not cleaned_candidates:
        return ""
    return max(
        cleaned_candidates, key=lambda value: (_text_quality_score(value), len(value))
    )


def _repair_mojibake_text(value: str) -> str:
    text = str(value or "")
    if not text or not _looks_mojibake(text):
        return text

    candidates = [text]
    for source_encoding in ("cp1250", "latin1", "cp1252"):
        try:
            repaired = text.encode(source_encoding, errors="ignore").decode(
                "utf-8", errors="ignore"
            )
        except Exception:
            continue
        repaired = repaired.strip()
        if repaired:
            candidates.append(repaired)
    return max(candidates, key=_text_quality_score)


def _decode_text_bytes(data: bytes) -> str:
    candidates: list[str] = []
    for encoding in (
        "utf-8",
        "utf-8-sig",
        "cp1251",
        "windows-1251",
        "cp1250",
        "cp1252",
        "latin-1",
    ):
        try:
            decoded = data.decode(encoding)
            candidates.append(_repair_mojibake_text(decoded))
        except Exception:
            continue
    if candidates:
        return max(candidates, key=_text_quality_score)
    return _repair_mojibake_text(data.decode("utf-8", errors="ignore"))


def _extract_pdf_text_pypdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency optional at runtime
        raise ValueError(
            "PDF extraction is unavailable. Install `pypdf` package."
        ) from exc

    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        cleaned = _clean_extracted_text(text)
        if cleaned:
            parts.append(cleaned)
    return _clean_extracted_text("\n\n".join(parts))


def _extract_pdf_text_pdfminer(data: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency optional at runtime
        raise ValueError(
            "PDF fallback extraction is unavailable. Install `pdfminer.six` package."
        ) from exc

    text = extract_text(BytesIO(data)) or ""
    return _clean_extracted_text(text)


def _extract_pdf_text_ocr(data: bytes) -> str:
    import shutil

    poppler_ok = shutil.which("pdftoppm") or shutil.which("pdfinfo")
    tesseract_ok = shutil.which("tesseract")

    if not poppler_ok or not tesseract_ok:
        missing = []
        if not poppler_ok:
            missing.append("Poppler (pdftoppm)")
        if not tesseract_ok:
            missing.append("Tesseract OCR")

        detail = f"Missing dependencies for OCR: {', '.join(missing)}. "
        if "Windows" in __import__("platform").system():
            detail += "\nTo fix on Windows:\n1. Download Poppler for Windows and add 'bin' folder to PATH.\n2. Install Tesseract OCR for Windows and add to PATH."
        raise ValueError(detail)

    try:
        import pytesseract  # type: ignore
        from pdf2image import convert_from_bytes  # type: ignore
    except Exception as exc:
        raise ValueError(
            "OCR libraries (pytesseract/pdf2image) are not installed correctly."
        ) from exc

    images = convert_from_bytes(data, dpi=220, fmt="png")
    parts: list[str] = []
    for image in images[:MAX_OCR_PAGES]:
        best = ""
        for lang in ("ukr+eng", "ukr", "eng"):
            try:
                candidate = _clean_extracted_text(
                    pytesseract.image_to_string(image, lang=lang)
                )
            except Exception:
                continue
            if len(candidate) > len(best):
                best = candidate
        if best:
            parts.append(best)
    return _clean_extracted_text("\n\n".join(parts))


def _extract_pdf_text_pdftotext(data: bytes) -> str:
    # Uses external Poppler utility when installed in OS PATH.
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            temp_path = tmp.name

        completed = subprocess.run(
            ["pdftotext", "-layout", temp_path, "-"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if completed.returncode != 0:
            return ""
        return _clean_extracted_text(completed.stdout or "")
    except Exception:
        return ""
    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass


def _extract_pdf_text(data: bytes) -> str:
    candidates: list[str] = []

    try:
        pypdf_text = _extract_pdf_text_pypdf(data)
        if pypdf_text:
            candidates.append(pypdf_text)
    except Exception:
        pass

    best = _select_best_text_candidate(candidates)
    if len(best) >= MIN_PDF_TEXT_CHARS:
        return best

    try:
        pdfminer_text = _extract_pdf_text_pdfminer(data)
        if pdfminer_text:
            candidates.append(pdfminer_text)
    except Exception:
        pass

    best = _select_best_text_candidate(candidates)
    if len(best) >= MIN_PDF_TEXT_CHARS:
        return best

    try:
        external_text = _extract_pdf_text_pdftotext(data)
        if external_text:
            candidates.append(external_text)
    except Exception:
        pass

    best = _select_best_text_candidate(candidates)
    if len(best) >= MIN_PDF_TEXT_CHARS:
        return best

    # Last resort for image-only/scanned PDFs.
    try:
        ocr_text = _extract_pdf_text_ocr(data)
        if ocr_text:
            candidates.append(ocr_text)
    except Exception:
        pass

    return _select_best_text_candidate(candidates)


def _extract_docx_text(data: bytes) -> str:
    try:
        from docx import Document  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency optional at runtime
        raise ValueError(
            "DOCX extraction is unavailable. Install `python-docx` package."
        ) from exc

    document = Document(BytesIO(data))
    parts = [
        _clean_extracted_text(paragraph.text)
        for paragraph in document.paragraphs
        if (paragraph.text or "").strip()
    ]
    return _clean_extracted_text("\n".join(parts))


def _extract_image_text(data: bytes) -> str:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency optional at runtime
        raise ValueError(
            "Image OCR is unavailable. Install `pytesseract` and `Pillow` packages, and Tesseract OCR."
        ) from exc

    image = Image.open(BytesIO(data))
    text = pytesseract.image_to_string(
        image, lang="ukr+eng"
    )  # Support Ukrainian and English
    return _clean_extracted_text(text)


def _extract_audio_text(data: bytes) -> str:
    # Placeholder for audio transcription; requires speech recognition library like speech_recognition or external API
    # For now, return empty or mock
    return ""  # TODO: Implement with speech_recognition or cloud service


def extract_text_from_file(
    *, file_name: str, content_type: str | None, data: bytes
) -> str:
    suffix = Path(file_name or "").suffix.lower()
    normalized_content_type = (content_type or "").lower()

    if suffix in TEXT_EXTENSIONS or normalized_content_type.startswith("text/"):
        return _clean_extracted_text(_decode_text_bytes(data))
    if suffix == ".pdf" or "pdf" in normalized_content_type:
        return _extract_pdf_text(data)
    if suffix == ".docx" or "wordprocessingml" in normalized_content_type:
        return _extract_docx_text(data)
    if suffix in IMAGE_EXTENSIONS or normalized_content_type.startswith("image/"):
        return _extract_image_text(data)
    if suffix in AUDIO_EXTENSIONS or normalized_content_type.startswith("audio/"):
        return _extract_audio_text(data)
    if suffix in {".doc", ".rtf"}:
        return _clean_extracted_text(_decode_text_bytes(data))

    # Fallback for unknown formats: try raw decode to avoid hard failure for plain-text uploads with wrong MIME.
    return _clean_extracted_text(_decode_text_bytes(data))
