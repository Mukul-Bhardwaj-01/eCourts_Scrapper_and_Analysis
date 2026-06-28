"""
pdf_extractor.py
─────────────────────────
Extracts clean text from downloaded court order PDFs.

Flow:
    PDF
      ↓
    pdfplumber extraction
      ↓
    if scanned → OCR fallback
      ↓
    cleaning
      ↓
    return text
"""

import os
import re

import pdfplumber

from config import DEBUG

# Optional OCR support
OCR_AVAILABLE = False

try:
    import pytesseract
    from pdf2image import convert_from_path

    OCR_AVAILABLE = True

except Exception:
    OCR_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# RAW EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_raw_text(pdf_path: str) -> str:

    if not pdf_path:
        return ""

    if not os.path.exists(pdf_path):
        return ""

    pages = []

    try:

        with pdfplumber.open(pdf_path) as pdf:

            for page in pdf.pages:

                try:
                    text = page.extract_text()

                    if text:
                        pages.append(text)

                except Exception:
                    continue

    except Exception as e:

        if DEBUG:
            print(
                f"[pdf] extraction failed: "
                f"{pdf_path} : {e}"
            )

        return ""

    return "\n".join(pages)


# ─────────────────────────────────────────────────────────────────────────────
# OCR FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def ocr_pdf(pdf_path: str) -> str:

    if not OCR_AVAILABLE:
        return ""

    try:

        pages = convert_from_path(
            pdf_path,
            dpi=200,
        )

        text = []

        # limit OCR cost
        for page in pages[:5]:

            try:
                page_text = (
                    pytesseract
                    .image_to_string(page)
                )

                if page_text:
                    text.append(page_text)

            except Exception:
                continue

        return "\n".join(text)

    except Exception as e:

        if DEBUG:
            print(
                f"[pdf] OCR failed: {e}"
            )

        return ""


# ─────────────────────────────────────────────────────────────────────────────
# CLEANING
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(raw: str) -> str:

    if not raw:
        return ""

    text = raw

    # page numbering
    text = re.sub(
        r"\bPage\s+\d+\s+of\s+\d+\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b\d+\s*\|\s*P\s*a\s*g\s*e\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^\s*[-–]\s*\d+\s*[-–]\s*$",
        "",
        text,
        flags=re.MULTILINE,
    )

    # remove invisible unicode junk
    text = re.sub(
        r"[\u200b-\u200d\ufeff]",
        "",
        text,
    )

    # collapse spaces
    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text,
    )

    # collapse blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    # trim lines
    text = "\n".join(
        line.rstrip()
        for line in text.split("\n")
    )

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# METADATA
# ─────────────────────────────────────────────────────────────────────────────

def get_pdf_metadata(pdf_path: str):

    meta = {
        "pages": 0,
        "has_text": False,
        "size_kb": 0,
        "characters": 0,
    }

    if not pdf_path:
        return meta

    if not os.path.exists(pdf_path):
        return meta

    try:

        meta["size_kb"] = (
            os.path.getsize(pdf_path)
            // 1024
        )

        with pdfplumber.open(pdf_path) as pdf:

            meta["pages"] = len(pdf.pages)

            if pdf.pages:

                first = (
                    pdf.pages[0]
                    .extract_text()
                )

                meta["has_text"] = bool(first)

                if first:
                    meta["characters"] = len(first)

    except Exception:
        pass

    return meta


# ─────────────────────────────────────────────────────────────────────────────
# MAIN API
# ─────────────────────────────────────────────────────────────────────────────

def extract_order_text(pdf_path: str) -> str:

    raw = extract_raw_text(pdf_path)

    clean = clean_text(raw)

    if clean:
        return clean

    # try OCR
    meta = get_pdf_metadata(pdf_path)

    if (
        meta["pages"] > 0
        and not meta["has_text"]
    ):

        if DEBUG:
            print(
                f"[pdf] scanned pdf detected "
                f"({meta['pages']} pages)"
            )

        ocr_text = ocr_pdf(pdf_path)

        clean = clean_text(ocr_text)

        if clean:
            return clean

    return ""