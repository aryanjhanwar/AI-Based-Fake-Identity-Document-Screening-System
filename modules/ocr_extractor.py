"""
OCR extraction for Indian identity documents (Aadhaar, PAN, Passport).
Uses PaddleOCR PP-OCRv5 mobile detection and recognition models for faster field extraction.
"""
from __future__ import annotations
import re
import numpy as np
from PIL import Image

# ── patterns ──────────────────────────────────────────────────────────────────
_PAN_RE      = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_AADHAAR_RE  = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_DOB_RE      = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b")
_EXPIRY_RE   = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}\b")
_PHONE_RE    = re.compile(r"\b[6-9]\d{9}\b")

_BOILERPLATE = {
    "income", "tax", "dept", "department", "govt", "government", "of", "india",
    "permanent", "account", "number", "signature", "sign", "pan", "aadhaar",
    "aadhar", "address", "father", "mother", "republic", "welfare", "finance",
    "legislative", "female", "male", "gender", "unique", "identification",
    "authority", "uidai", "card", "the", "and", "for", "to", "a",
}
_HEADER_PHRASES = (
    "government of india",
    "govt of india",
    "income tax department",
    "permanent account number",
    "republic of india",
    "unique identification authority",
    "authority of india",
)

import threading
from config import OCR_KWARGS

_ocr_lock = threading.Lock()
_ocr_instance = None

def _get_ocr():
    global _ocr_instance
    with _ocr_lock:
        if _ocr_instance is not None:
            return _ocr_instance
        import os
        os.environ.setdefault("FLAGS_enable_pir_api", "0")
        try:
            import paddle
            paddle.set_flags({"FLAGS_enable_pir_api": 0})
        except Exception:
            pass
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(**OCR_KWARGS)
        return _ocr_instance


def _parse_lines(result) -> list[dict]:
    lines = []
    for r in result:
        texts  = r.get("rec_texts") or []
        boxes  = r.get("rec_polys") or r.get("rec_boxes") or []
        scores = r.get("rec_scores") or []
        for t, b, s in zip(texts, boxes, scores):
            t = re.sub(r"\s+", " ", str(t)).strip()
            if not t:
                continue
            xs = [p[0] for p in b]; ys = [p[1] for p in b]
            lines.append({
                "text": t,
                "box":  [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                "conf": float(s),
            })
    # Sort top-to-bottom, left-to-right (reading order)
    lines.sort(key=lambda l: (l["box"][1], l["box"][0]))
    return lines


def _name_candidate(line_text: str) -> str | None:
    """Return text if it looks like a person's name, else None."""
    if any(char.isdigit() for char in line_text):
        return None
    t = re.sub(r"[^A-Za-z .\-']", "", line_text).strip()
    normalized = re.sub(r"[^a-z ]", " ", t.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if any(phrase in normalized for phrase in _HEADER_PHRASES):
        return None
    words = [w for w in t.split() if len(w) >= 2]
    if len(words) < 1 or len(t) < 3:
        return None
    if all(w.lower() in _BOILERPLATE for w in words):
        return None
    # Accept ALL-CAPS or Title Case
    clean = [w for w in words if w.isalpha() and (w.isupper() or w.istitle())]
    if len(clean) >= 1 and len(clean) == len(words):
        return " ".join(clean)
    return None


def calculate_age(dob_str: str | None) -> int | None:
    if not dob_str:
        return None
    from datetime import datetime
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(str(dob_str).strip(), fmt)
            if dt.year > datetime.now().year:
                dt = dt.replace(year=dt.year - 100)
            today = datetime.now()
            age = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
            if 0 <= age <= 120:
                return age
        except ValueError:
            continue
    yr_m = re.search(r"\b(19\d{2}|20[0-2]\d)\b", str(dob_str))
    if yr_m:
        birth_year = int(yr_m.group(1))
        age = datetime.now().year - birth_year
        if 0 <= age <= 120:
            return age
    return None


def extract(img: Image.Image) -> dict:
    """
    Run OCR and extract structured fields.
    Returns: fields dict + raw lines + risk score + findings list.
    """
    img = img.convert("RGB")
    # Scale down to 720px max to significantly speed up OCR inference while keeping text crisp
    max_dim = 720
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.BILINEAR)

    # PaddleOCR 3.x accepts NumPy arrays or file paths, not PIL images.
    result = _get_ocr().predict(np.asarray(img))
    lines  = _parse_lines(result)
    full_text = " ".join(l["text"] for l in lines)
    full_upper = full_text.upper().replace(" ", "")
    full_lower = full_text.lower()

    # ── field extraction ──────────────────────────────────────────────────────
    pan_m     = _PAN_RE.search(full_upper)
    aadhaar_m = _AADHAAR_RE.search(full_text)
    dob_m     = _DOB_RE.search(full_text)
    phone_m   = _PHONE_RE.search(full_text)

    # Expiry: look near "expiry/expires/valid" label
    expiry = None
    for i, l in enumerate(lines):
        if re.search(r"expir|valid until|valid thru", l["text"], re.I):
            ctx = " ".join(lines[j]["text"] for j in range(max(0, i-1), min(len(lines), i+3)))
            m = _EXPIRY_RE.search(ctx)
            if m:
                expiry = m.group(0)
                break

    # Name: prefer a labeled name, otherwise choose the strongest OCR
    # candidate. This prevents low-confidence header artifacts from winning.
    name_candidates: list[tuple[float, str]] = []
    for l in lines:
        n = _name_candidate(l["text"])
        if n and len(n.replace(" ", "")) >= 4:
            words = n.split()
            score = float(l["conf"]) + min(len(words), 4) * 0.08
            if re.search(r"\b(name|surname|given names?)\b", l["text"], re.I):
                score += 0.25
            name_candidates.append((score, n))
    name = max(name_candidates, default=(0.0, None), key=lambda candidate: candidate[0])[1]

    # Father/Spouse name
    father_name = None
    for i, l in enumerate(lines):
        if re.search(r"father|s/o|d/o|w/o|husband|spouse", l["text"], re.I):
            # Try same line first, then next line
            for j in (i, i+1):
                if 0 <= j < len(lines):
                    n = _name_candidate(lines[j]["text"])
                    if n and n != name:
                        father_name = n
                        break
            if father_name:
                break

    # Gender
    gender = None
    gm = re.search(r"\b(MALE|FEMALE)\b", full_text, re.I)
    if gm:
        gender = gm.group(0).title()
    elif re.search(r"\bM\b", full_text) and re.search(r"sex|gender", full_lower):
        gender = "Male"
    elif re.search(r"\bF\b", full_text) and re.search(r"sex|gender", full_lower):
        gender = "Female"

    # Detect MRZ (passport)
    mrz = [l["text"] for l in lines if re.fullmatch(r"[A-Z0-9<]{30,}", l["text"])]

    # Document type detection
    doc_type = "unknown"
    if mrz or re.search(r"passport", full_lower):
        doc_type = "passport"
    elif re.search(r"permanent account|income tax|pan\b", full_lower) or pan_m:
        doc_type = "pan"
    elif re.search(r"aadhaar|uidai|uid\b|unique identification", full_lower) or aadhaar_m:
        doc_type = "aadhaar"
    elif re.search(r"driving|licence|license", full_lower):
        doc_type = "driving_license"
    elif re.search(r"voter|election", full_lower):
        doc_type = "voter_id"

    dob = dob_m.group(0) if dob_m else None
    age = calculate_age(dob)
    if age is None:
        age_m = re.search(r"\b(?:age|years|yr|yrs)\b[:\s\-]*([1-9][0-9])\b", full_lower)
        if age_m:
            try:
                age = int(age_m.group(1))
            except ValueError:
                pass

    id_number = None
    if pan_m:
        id_number = pan_m.group(0)
    elif aadhaar_m:
        id_number = aadhaar_m.group(0).replace("-", " ").replace("  ", " ")
    elif mrz and len(mrz) > 0:
        id_number = mrz[0][:10]

    fields = {
        "doc_type":     doc_type,
        "name":         name,
        "father_name":  father_name,
        "dob":          dob,
        "age":          age,
        "gender":       gender,
        "id_number":    id_number,
        "pan_number":   pan_m.group(0) if pan_m else None,
        "aadhaar_number": aadhaar_m.group(0).replace("-", " ").replace("  ", " ") if aadhaar_m else None,
        "expiry":       expiry,
        "phone":        phone_m.group(0) if phone_m else None,
        "mrz_line1":    mrz[0] if len(mrz) > 0 else None,
        "mrz_line2":    mrz[1] if len(mrz) > 1 else None,
    }

    # ── validation / risk ─────────────────────────────────────────────────────
    risk     = 0.0
    findings = []

    if doc_type == "pan":
        if not pan_m:
            findings.append("PAN number not detected or invalid format")
            risk += 0.5
        else:
            findings.append(f"PAN number extracted: {pan_m.group(0)}")
        if not dob_m:
            findings.append("Date of birth missing")
            risk += 0.2

    elif doc_type == "aadhaar":
        if not aadhaar_m:
            findings.append("Aadhaar number not detected")
            risk += 0.5
        else:
            # Validate 12 digits
            digits = re.sub(r"\D", "", aadhaar_m.group(0))
            if len(digits) != 12:
                findings.append(f"Aadhaar has invalid digit count: {len(digits)}")
                risk += 0.4
            else:
                findings.append(f"Aadhaar number extracted: {aadhaar_m.group(0)}")
        if not dob_m:
            findings.append("Date of birth missing")
            risk += 0.2

    elif doc_type == "passport":
        if not mrz:
            findings.append("No MRZ detected — cannot verify passport integrity")
            risk += 0.6
        if not expiry:
            findings.append("Expiry date not detected")
            risk += 0.1

    elif doc_type == "unknown":
        findings.append("Could not determine document type")
        risk += 0.3

    if not name:
        findings.append("Name could not be extracted")
        risk += 0.15

    # Check DOB sanity (year should be reasonable)
    if dob_m:
        yr_m = re.search(r"\d{4}", dob_m.group(0))
        if yr_m:
            yr = int(yr_m.group(0))
            if not (1900 < yr < 2015):
                findings.append(f"Suspicious year in DOB: {yr}")
                risk += 0.3

    # Expiry check
    if expiry and doc_type == "passport":
        yr_m = re.search(r"\d{4}", expiry)
        if yr_m and int(yr_m.group(0)) < 2024:
            findings.append("Document appears expired")
            risk += 0.2

    risk = round(min(risk, 1.0), 4)

    return {
        "fields":   fields,
        "lines":    lines,
        "risk":     risk,
        "findings": findings,
        "raw_text": full_text[:2000],
    }
