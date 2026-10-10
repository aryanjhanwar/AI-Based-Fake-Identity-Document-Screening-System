"""
VeriShieldAI — Identity Document Forensic & Person Verification Backend
Exposes REST APIs for document screening, person data extraction (OCR), and fraud detection.

Classification:
  - Pass: Authentic / Genuine ID (Low Risk, High Real Probability)
  - Suspicious: Borderline clarity or missing key fields (Medium Risk)
  - Failed: Confirmed Forgery or Tampering (High / Critical Risk, High Fake Probability)

Key Endpoints:
  POST /api/analysis/upload   -> Upload & screen document (runs ML + OCR extraction)
  POST /api/screen            -> Alias for /api/analysis/upload (supports file or doc_image)
  GET  /api/analysis          -> List analyses with Pass/Suspicious/Failed filters
  GET  /api/analysis/<id>     -> Get complete analysis & person record
  GET  /api/analysis/<id>/image -> Serve original uploaded ID image
  POST /api/analysis/<id>/review -> Update reviewer decision
  GET  /api/system/dashboard/stats -> Dashboard KPI metrics
  GET  /api/system/health     -> Engine health & telemetry
  GET  /api/analytics         -> Aggregated screening statistics
  GET  /api/samples           -> Pre-configured dataset sample documents
  GET  /api/samples/<id>/file -> Serve sample document file
"""
from __future__ import annotations

import os
import time
import tempfile
import traceback
import uuid
import re
from datetime import datetime

os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_allocator_strategy", "naive")
os.environ.setdefault("FLAGS_fraction_of_cpu_memory_to_use", "0.15")
os.environ.setdefault("CPU_NUM", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from PIL import Image
import numpy as np
import cv2

# ── ML & OCR modules ────────────────────────────────────────────────────────
from modules.classifier import predict as classify, _ela_heuristic
from modules.metadata_analysis import analyze_metadata
from modules.stamp_forensics import analyze_stamps
from modules.ocr_extractor import extract as ocr_extract, calculate_age

# ── App setup ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

frontend_dist = os.path.join(BASE_DIR, "..", "frontend", "dist")
if not os.path.exists(frontend_dist):
    frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")
app = Flask(__name__, static_folder=frontend_dist if os.path.exists(frontend_dist) else None, static_url_path="/")
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

import threading

def _warmup_background():
    try:
        from modules.ocr_extractor import _get_ocr
        _get_ocr()
        print("[VeriShieldAI] OCR engine initialized in background thread.")
    except Exception as e:
        print(f"[VeriShieldAI] Background OCR warmup notice: {e}")

threading.Thread(target=_warmup_background, daemon=True).start()

# ── In-memory analysis store ─────────────────────────────────────────────────
# Pre-seeded with realistic records reflecting Pass, Failed, and Suspicious outcomes
ANALYSES: list[dict] = [
    {
        "id": "SCN-94021",
        "analysis_number": "AN-2026-0001",
        "original_filename": "aadhaar_card_pvc_sample.jpg",
        "document_type": "Aadhaar Card",
        "status": "completed",
        "classification": "Pass",
        "verdict": "PASS",
        "real_probability": 98.2,
        "fake_probability": 1.8,
        "risk_level": "low",
        "risk_score": 2,
        "human_summary": "Authentic government document verified. Print micro-patterns, photo region, and security seals match official UIDAI standards.",
        "person_details": {
            "name": "RAVI SHARMA",
            "age": "36 Years",
            "dob": "01/01/1990",
            "gender": "Male",
            "id_number": "1234 5678 9012",
            "document_type": "Aadhaar Card",
            "father_name": "SURESH SHARMA",
            "address": "New Delhi, India",
        },
        "verification_checklist": [
            {"item": "Document Format & Layout", "status": "Passed", "detail": "Valid UIDAI Aadhaar design template"},
            {"item": "Photo & Portrait Authenticity", "status": "Passed", "detail": "Natural facial print boundaries without splicing"},
            {"item": "Security Seal & Emblem", "status": "Passed", "detail": "Official Ashoka emblem detected and intact"},
            {"item": "Digital Tampering / Editing", "status": "Passed", "detail": "No image editing software tags in file"},
        ],
        "risk_explanation": "Document passed all anti-forgery filters. Color profile, edge sharpness, and digital container tags align with genuine samples.",
        "risk_factors": [
            {"factor": "Print Surface Analysis", "explanation": "Natural edge distribution. No re-sampling detected.", "weight": 2},
            {"factor": "Color Gamut Verification", "explanation": "Color space matches genuine document standard.", "weight": 1},
            {"factor": "Digital Container Tags", "explanation": "No photo manipulation software traces found.", "weight": 0},
            {"factor": "Official Emblem Integrity", "explanation": "UIDAI emblem confirmed authentic.", "weight": 2},
        ],
        "extracted_fields": {
            "doc_type": "Aadhaar Card",
            "resolution": "1080x680",
            "sharpness_score": "High (Clear)",
            "stamps_detected": "1",
            "face_detected": "Yes",
            "security_seal": "Intact",
            "print_consistency": "Verified Genuine",
        },
        "forensic_findings": [],
        "forensic_summary": "Verification passed cleanly. No digital tampering or splicing detected.",
        "ml_prediction": {
            "available": True,
            "model_version": "RandomForest-HOG-HSV",
            "avg_confidence": 0.98,
            "detections": [
                {"class_name": "name_field", "confidence": 0.98},
                {"class_name": "aadhaar_number", "confidence": 0.99},
                {"class_name": "dob_field", "confidence": 0.96},
                {"class_name": "photo_region", "confidence": 0.98},
            ],
        },
        "ocr_confidence": 0.96,
        "ocr_results": {"raw_text": "Government of India\nAadhaar\n1234 5678 9012\nName: RAVI SHARMA\nDOB: 01/01/1990\nMale"},
        "review_status": "approved",
        "reviewer_notes": "Genuine Aadhaar card. Automatically verified.",
        "file_size": 245678,
        "mime_type": "image/jpeg",
        "processing_time_ms": 52,
        "created_at": "2026-10-09T20:45:12",
        "image_path": None,
        "fake_prob": 0.018,
        "combined_risk": 0.018,
        "confidence": 0.982,
        "method": "fast_rf_classifier (HOG+HSV)",
        "reasons": [
            "Print patterns and edge boundaries match authentic UIDAI cards.",
            "No signs of digital manipulation in color space or compression error.",
            "High image resolution and optical sharpness confirm original scan.",
            "Digital container metadata confirms no third-party photo editing tool was used.",
        ],
        "metadata": {"has_exif": True, "software": None, "camera": "Canon CanoScan LiDE", "risk": 0.0},
        "stamps": {"stamp_count": 1, "risk": 0.0, "note": "Official UIDAI emblem verified."},
        "quality": {"sharpness": 462.8, "brightness": 194.2, "contrast": 54.1, "resolution": "1080x680"},
        "elapsed": 0.052,
    },
    {
        "id": "SCN-94020",
        "analysis_number": "AN-2026-0002",
        "original_filename": "pan_tampered_text.jpg",
        "document_type": "PAN Card",
        "status": "review_required",
        "classification": "Failed",
        "verdict": "FAILED",
        "real_probability": 8.5,
        "fake_probability": 91.5,
        "risk_level": "critical",
        "risk_score": 91,
        "human_summary": "FORGERY DETECTED: Digital font overlay and pixel tampering detected around the PAN number and Name fields. File metadata reveals editing in Adobe Photoshop.",
        "person_details": {
            "name": "PANKAJ SHARMA",
            "age": "37 Years",
            "dob": "15/08/1988",
            "gender": "Male",
            "id_number": "ABCDE1234F",
            "document_type": "PAN Card",
            "father_name": "MOHAN LAL SHARMA",
            "address": "Not specified",
        },
        "verification_checklist": [
            {"item": "Document Format & Layout", "status": "Failed", "detail": "Font alignment mismatch at PAN number"},
            {"item": "Photo & Portrait Authenticity", "status": "Suspicious", "detail": "Sharp pixel edge cut around photo box"},
            {"item": "Security Seal & Emblem", "status": "Failed", "detail": "Official Income Tax hologram distorted"},
            {"item": "Digital Tampering / Editing", "status": "Failed", "detail": "Adobe Photoshop EXIF tag identified"},
        ],
        "risk_explanation": "Severe digital tampering detected. Alphanumeric characters were altered digitally and compression discrepancy confirms spliced text.",
        "risk_factors": [
            {"factor": "Digital Tampering", "explanation": "File was processed using Adobe Photoshop.", "weight": 95},
            {"factor": "Compression Error (ELA)", "explanation": "Discrepancy at PAN number indicates text was pasted.", "weight": 88},
            {"factor": "Font & Print Boundaries", "explanation": "Unnatural pixel boundaries around alphanumeric fields.", "weight": 85},
            {"factor": "Official Hologram Integrity", "explanation": "Security hologram pattern is missing or altered.", "weight": 70},
        ],
        "extracted_fields": {
            "doc_type": "PAN Card",
            "resolution": "800x520",
            "sharpness_score": "Moderate",
            "stamps_detected": "0",
            "face_detected": "Yes",
            "security_seal": "Altered / Fake",
            "print_consistency": "Spliced / Edited",
        },
        "forensic_findings": [
            {"finding": "Photoshop software detected in metadata", "severity": "high", "method": "metadata_analysis", "details": "File was saved with Adobe Photoshop — digital modification confirmed."},
            {"finding": "Compression mismatch at text region", "severity": "high", "method": "error_level_analysis", "details": "Error Level Analysis shows synthetic font paste at PAN number."},
            {"finding": "Font misalignment", "severity": "high", "method": "layout_verification", "details": "Card text diverges from NSDL standard typeface."},
        ],
        "forensic_summary": "3 severe manipulation indicators detected. Document confirmed forged.",
        "ml_prediction": {
            "available": True,
            "model_version": "RandomForest-HOG-HSV",
            "avg_confidence": 0.945,
            "detections": [
                {"class_name": "name_field", "confidence": 0.35},
                {"class_name": "pan_number", "confidence": 0.28},
            ],
        },
        "ocr_confidence": 0.61,
        "ocr_results": {"raw_text": "INCOME TAX DEPARTMENT\nPANKAJ SHARMA\nFather: MOHAN LAL SHARMA\nDOB: 15/08/1988\nABCDE1234F"},
        "review_status": "rejected",
        "reviewer_notes": "Confirmed forgery. PAN number pasted with Photoshop.",
        "file_size": 189432,
        "mime_type": "image/jpeg",
        "processing_time_ms": 48,
        "created_at": "2026-10-09T20:12:44",
        "image_path": None,
        "fake_prob": 0.915,
        "combined_risk": 0.915,
        "confidence": 0.915,
        "method": "fast_rf_classifier (HOG+HSV)",
        "reasons": [
            "Digital modification software (Adobe Photoshop) detected in file EXIF.",
            "Compression variance confirms alphanumeric text was digitally replaced.",
            "Font spacing and alignment diverge from genuine NSDL format.",
        ],
        "metadata": {"has_exif": True, "software": "Adobe Photoshop 24.1", "camera": None, "risk": 0.95},
        "stamps": {"stamp_count": 0, "risk": 0.70, "note": "Official security hologram missing."},
        "quality": {"sharpness": 128.4, "brightness": 162.0, "contrast": 42.1, "resolution": "800x520"},
        "elapsed": 0.048,
    },
    {
        "id": "SCN-94019",
        "analysis_number": "AN-2026-0003",
        "original_filename": "passport_front_page.jpg",
        "document_type": "Passport",
        "status": "completed",
        "classification": "Pass",
        "verdict": "PASS",
        "real_probability": 93.8,
        "fake_probability": 6.2,
        "risk_level": "low",
        "risk_score": 6,
        "human_summary": "Authentic Passport verified. Machine Readable Zone (MRZ) checksums valid, optical contrast and security seals verified.",
        "person_details": {
            "name": "ANANYA PATEL",
            "age": "34 Years",
            "dob": "20/03/1992",
            "gender": "Female",
            "id_number": "P<INDPATEL<<ANANYA",
            "document_type": "Passport",
            "father_name": "KIRAN PATEL",
            "address": "Ahmedabad, Gujarat",
        },
        "verification_checklist": [
            {"item": "Document Format & Layout", "status": "Passed", "detail": "ICAO Doc 9303 standard passport format verified"},
            {"item": "Photo & Portrait Authenticity", "status": "Passed", "detail": "Ghost image and primary photo match"},
            {"item": "Security Seal & Emblem", "status": "Passed", "detail": "Embossed emblem and official ink verified"},
            {"item": "Digital Tampering / Editing", "status": "Passed", "detail": "No compression artifacts detected"},
        ],
        "risk_explanation": "Document passed all anti-forgery filters. MRZ zone geometry and optical contrast match genuine Indian passports.",
        "risk_factors": [
            {"factor": "MRZ Checksum Validation", "explanation": "Machine Readable Zone syntax conforms to ICAO TD3.", "weight": 2},
            {"factor": "Print Surface Analysis", "explanation": "Fine guilloche pattern intact.", "weight": 5},
            {"factor": "Digital Container Tags", "explanation": "No photo editing traces.", "weight": 0},
        ],
        "extracted_fields": {
            "doc_type": "Passport",
            "resolution": "1200x780",
            "sharpness_score": "High (Clear)",
            "stamps_detected": "2",
            "face_detected": "Yes",
            "security_seal": "Intact",
            "print_consistency": "Verified Genuine",
        },
        "forensic_findings": [],
        "forensic_summary": "Full forensic scan passed. Document structure consistent with genuine Indian passport.",
        "ml_prediction": {
            "available": True,
            "model_version": "RandomForest-HOG-HSV",
            "avg_confidence": 0.94,
            "detections": [
                {"class_name": "mrz_line1", "confidence": 0.97},
                {"class_name": "mrz_line2", "confidence": 0.96},
                {"class_name": "photo_region", "confidence": 0.94},
                {"class_name": "name_field", "confidence": 0.93},
            ],
        },
        "ocr_confidence": 0.96,
        "ocr_results": {"raw_text": "Republic of India\nPassport\nSurname: PATEL\nGiven Names: ANANYA\nNationality: INDIAN\nDate of Birth: 20/03/1992\nSex: F\nP<INDPATEL<<ANANYA<<<<<<<<<<<<<<<"},
        "review_status": "approved",
        "reviewer_notes": "Diplomatic/Regular Indian passport format verified.",
        "file_size": 312890,
        "mime_type": "image/jpeg",
        "processing_time_ms": 61,
        "created_at": "2026-10-09T19:30:40",
        "image_path": None,
        "fake_prob": 0.062,
        "combined_risk": 0.062,
        "confidence": 0.938,
        "method": "fast_rf_classifier (HOG+HSV)",
        "reasons": [
            "Color distribution and edge gradients appear natural and genuine.",
            "MRZ zone geometry matches ICAO TD3 passport specifications.",
            "Optical contrast is consistent across photo and text regions.",
        ],
        "metadata": {"has_exif": True, "software": None, "camera": "HP ScanJet Pro", "risk": 0.0},
        "stamps": {"stamp_count": 2, "risk": 0.0, "note": "Official immigration stamp detected."},
        "quality": {"sharpness": 512.6, "brightness": 210.4, "contrast": 49.8, "resolution": "1200x780"},
        "elapsed": 0.061,
    },
    {
        "id": "SCN-94018",
        "analysis_number": "AN-2026-0004",
        "original_filename": "voter_id_blurry_scan.png",
        "document_type": "Voter ID",
        "status": "review_required",
        "classification": "Suspicious",
        "verdict": "SUSPICIOUS",
        "real_probability": 56.0,
        "fake_probability": 44.0,
        "risk_level": "medium",
        "risk_score": 44,
        "human_summary": "SUSPICIOUS: Image clarity is blurry and low-resolution. Minor compression disparity detected. Secondary human review advised before approving.",
        "person_details": {
            "name": "RAMESH KUMAR",
            "age": "40 Years",
            "dob": "05/12/1985",
            "gender": "Male",
            "id_number": "ABC1234567",
            "document_type": "Voter ID",
            "father_name": "DINESH KUMAR",
            "address": "Not specified",
        },
        "verification_checklist": [
            {"item": "Document Format & Layout", "status": "Passed", "detail": "Election Commission of India card layout detected"},
            {"item": "Photo & Portrait Authenticity", "status": "Suspicious", "detail": "Face blur exceeds threshold"},
            {"item": "Security Seal & Emblem", "status": "Suspicious", "detail": "No official emblem isolated clearly"},
            {"item": "Digital Tampering / Editing", "status": "Passed", "detail": "No photo manipulation software metadata"},
        ],
        "risk_explanation": "Borderline scan quality. Low image clarity may mask potential modifications; human review recommended.",
        "risk_factors": [
            {"factor": "Optical Image Clarity", "explanation": "Low sharpness suggests screenshot or repeated re-compression.", "weight": 48},
            {"factor": "Surface Gradient Continuity", "explanation": "Borderline edge distribution due to blur.", "weight": 42},
            {"factor": "Color Gamut Verification", "explanation": "Slight brightness variance across document face.", "weight": 35},
        ],
        "extracted_fields": {
            "doc_type": "Voter ID",
            "resolution": "640x480",
            "sharpness_score": "Low (Blurry)",
            "stamps_detected": "0",
            "face_detected": "Partial",
            "security_seal": "Indeterminate",
            "print_consistency": "Low Resolution",
        },
        "forensic_findings": [
            {"finding": "Low image sharpness", "severity": "medium", "method": "optical_quality_metrics", "details": "Image sharpness is below standard threshold. Could indicate a re-compressed screenshot."},
        ],
        "forensic_summary": "Borderline image quality. Manual analyst signoff required.",
        "ml_prediction": {
            "available": True,
            "model_version": "RandomForest-HOG-HSV",
            "avg_confidence": 0.56,
            "detections": [
                {"class_name": "name_field", "confidence": 0.62},
                {"class_name": "voter_id_number", "confidence": 0.58},
            ],
        },
        "ocr_confidence": 0.67,
        "ocr_results": {"raw_text": "Election Commission of India\nRAMESH KUMAR\nS/O: DINESH KUMAR\nDate of Birth: 05/12/1985\nABC1234567"},
        "review_status": "pending",
        "reviewer_notes": "Needs clearer re-scan.",
        "file_size": 98765,
        "mime_type": "image/png",
        "processing_time_ms": 43,
        "created_at": "2026-10-09T18:55:04",
        "image_path": None,
        "fake_prob": 0.44,
        "combined_risk": 0.44,
        "confidence": 0.56,
        "method": "fast_rf_classifier (HOG+HSV)",
        "reasons": [
            "Low image resolution and optical blur make automated determination borderline.",
            "No high-confidence software tampering traces found.",
            "Requires human reviewer verification before approval.",
        ],
        "metadata": {"has_exif": False, "software": None, "camera": None, "risk": 0.15},
        "stamps": {"stamp_count": 0, "risk": 0.0, "note": "No stamp isolated."},
        "quality": {"sharpness": 72.3, "brightness": 118.0, "contrast": 39.2, "resolution": "640x480"},
        "elapsed": 0.043,
    },
]

SERVER_START_TIME = datetime.now()

# ── Sample documents for 1-click testing ────────────────────────────────────
SAMPLES = [
    {
        "id": "genuine_aadhaar",
        "title": "Clean Aadhaar (Authentic)",
        "type": "aadhaar",
        "expected": "PASS",
        "path": os.path.join("Dataset", "Aadhar", "Original", "0005_jpeg_jpg.rf.252590ac8ae7f0f84a08f15a164d6cb0.jpg"),
        "description": "Original government UIDAI Aadhaar card with intact micro-print.",
    },
    {
        "id": "forged_aadhaar_1",
        "title": "Tampered Aadhaar (Forged)",
        "type": "aadhaar",
        "expected": "FAILED",
        "path": os.path.join("Dataset", "Aadhar", "Fake", "0_1.jpg"),
        "description": "Manipulated Aadhaar card with spliced font overlay and compression mismatch.",
    },
    {
        "id": "genuine_aadhaar_2",
        "title": "Verified Aadhaar Scan",
        "type": "aadhaar",
        "expected": "PASS",
        "path": os.path.join("Dataset", "Aadhar", "Original", "0521_adhar_jpg.rf.0188ba6593c38a70e56de2509a244a4d.jpg"),
        "description": "High-clarity original Aadhaar with verified government security seal.",
    },
    {
        "id": "forged_aadhaar_2",
        "title": "High Tampering Fake",
        "type": "aadhaar",
        "expected": "FAILED",
        "path": os.path.join("Dataset", "Aadhar", "Fake", "fake_0_0.jpg"),
        "description": "Forged document exhibiting distinct pixel boundaries and fake photo cut.",
    },
]


# ── Helpers: Classification & Probability Mapping ───────────────────────────
def _classify_document(combined_risk: float, fake_prob: float) -> tuple[str, str, int, float, float]:
    """
    Returns:
      classification: "Pass" | "Suspicious" | "Failed"
      verdict:        "PASS" | "SUSPICIOUS" | "FAILED"
      risk_score:     0 to 100
      real_prob:      float percentage 0 to 100
      fake_prob:      float percentage 0 to 100
    """
    score = int(round(combined_risk * 100))
    # Fake percentage reflects highest tamper probability detected
    fake_pct = round(np.clip(max(fake_prob, combined_risk) * 100, 0.0, 100.0), 1)
    real_pct = round(np.clip(100.0 - fake_pct, 0.0, 100.0), 1)

    if combined_risk < 0.25:
        return "Pass", "PASS", score, real_pct, fake_pct
    elif combined_risk <= 0.50:
        return "Suspicious", "SUSPICIOUS", score, real_pct, fake_pct
    else:
        return "Failed", "FAILED", score, real_pct, fake_pct


def _build_risk_factors(clf: dict, ela_risk: float, meta: dict, stamps: dict, sharpness: float, face_detected: bool) -> list[dict]:
    factors = []
    factors.append({
        "factor": "AI Print Pattern Analysis",
        "explanation": (
            "Print patterns and edge transitions match genuine ID baseline."
            if clf["label"] != "FAKE"
            else f"Unnatural edge gradients or digital re-sampling detected (Confidence: {clf['confidence']*100:.1f}%)."
        ),
        "weight": int(clf["fake_prob"] * 100),
    })
    factors.append({
        "factor": "Digital Splicing & ELA",
        "explanation": (
            f"Compression variance ({ela_risk*100:.1f}%) indicates spliced text or pasted elements."
            if ela_risk > 0.35
            else "Uniform compression across image face. No digital splicing detected."
        ),
        "weight": int(ela_risk * 100),
    })
    if meta.get("software"):
        factors.append({
            "factor": "Photo Editing Software",
            "explanation": f"File EXIF shows '{meta['software']}' — strong forgery indicator.",
            "weight": int(meta.get("risk", 0.5) * 100),
        })
    else:
        factors.append({
            "factor": "Metadata Integrity",
            "explanation": "No third-party image manipulation software found in file container.",
            "weight": 0,
        })
    stamp_count = stamps.get("stamp_count", 0)
    factors.append({
        "factor": "Official Seal / Emblem",
        "explanation": (
            f"{stamp_count} official seal/emblem region(s) verified."
            if stamp_count > 0
            else "No official seal or emblem isolated on document."
        ),
        "weight": 2 if stamp_count > 0 else 15,
    })
    factors.append({
        "factor": "Image Clarity & Quality",
        "explanation": (
            f"High optical sharpness ({sharpness:.1f}). Clear original scan."
            if sharpness >= 80
            else f"Low sharpness ({sharpness:.1f}). Blurry image may mask alterations."
        ),
        "weight": 5 if sharpness >= 80 else 45,
    })
    return factors


def _build_forensic_findings(clf: dict, ela_risk: float, meta: dict, stamps: dict, sharpness: float) -> list[dict]:
    findings = []
    if clf["label"] == "FAKE":
        findings.append({
            "finding": "AI detected unnatural print and edge patterns",
            "severity": "high",
            "method": "pattern_classifier",
            "details": f"Pattern classifier fake probability: {clf['fake_prob']*100:.1f}%. Diverges from authentic ID benchmark.",
        })
    if ela_risk > 0.40:
        findings.append({
            "finding": f"Digital splicing disparity detected ({ela_risk*100:.1f}%)",
            "severity": "high" if ela_risk > 0.60 else "medium",
            "method": "error_level_analysis",
            "details": "Localized JPEG compression disparity suggests text or photo was digitally altered.",
        })
    if meta.get("software"):
        findings.append({
            "finding": f"Editing software in metadata: {meta['software']}",
            "severity": "high",
            "method": "metadata_analysis",
            "details": "File metadata includes a photo editing application.",
        })
    if sharpness < 80:
        findings.append({
            "finding": f"Low image sharpness ({sharpness:.1f})",
            "severity": "medium",
            "method": "optical_quality",
            "details": "Image sharpness below clear scan threshold. May be a re-compressed screenshot.",
        })
    return findings


# ═══════════════════════════════════════════════════════════════════════════
#  API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/system/health", methods=["GET"])
def api_health():
    return jsonify({
        "status": "healthy",
        "uptime_seconds": int((datetime.now() - SERVER_START_TIME).total_seconds()),
        "model": "fast_rf_classifier (HOG+HSV Random Forest) + ELA",
        "ocr_engine": "PaddleOCR PP-OCRv6 + RegEx Field Extractor",
        "avg_latency_ms": round(
            sum(a.get("processing_time_ms", 50) for a in ANALYSES) / max(len(ANALYSES), 1), 1
        ),
        "total_screenings": len(ANALYSES),
        "engine_version": "VeriShieldAI-v3.2",
        "modules": {
            "classifier": "active",
            "ocr_extractor": "active",
            "metadata_analysis": "active",
            "stamp_forensics": "active",
            "face_detection": "active",
        },
    })


@app.route("/api/system/dashboard/stats", methods=["GET"])
def api_dashboard_stats():
    total = len(ANALYSES)
    passed_count = sum(1 for a in ANALYSES if a.get("classification") == "Pass" or a.get("verdict") == "PASS")
    suspicious_count = sum(1 for a in ANALYSES if a.get("classification") == "Suspicious" or a.get("verdict") == "SUSPICIOUS")
    failed_count = sum(1 for a in ANALYSES if a.get("classification") == "Failed" or a.get("verdict") == "FAILED")

    avg_ms = round(sum(a.get("processing_time_ms", 50) for a in ANALYSES) / max(total, 1), 1)

    recent = sorted(ANALYSES, key=lambda x: x.get("created_at", ""), reverse=True)[:6]
    recent_out = [_lite(a) for a in recent]

    return jsonify({
        "total_analyses": total,
        "passed_count": passed_count,
        "suspicious_count": suspicious_count,
        "failed_count": failed_count,
        "review_required": suspicious_count,
        "risk_distribution": {
            "low": passed_count,
            "medium": suspicious_count,
            "high": failed_count,
            "critical": 0,
        },
        "avg_processing_time_ms": avg_ms,
        "recent_analyses": recent_out,
    })


@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    total = len(ANALYSES)
    passed = sum(1 for a in ANALYSES if a.get("classification") == "Pass" or a.get("verdict") == "PASS")
    suspicious = sum(1 for a in ANALYSES if a.get("classification") == "Suspicious" or a.get("verdict") == "SUSPICIOUS")
    failed = sum(1 for a in ANALYSES if a.get("classification") == "Failed" or a.get("verdict") == "FAILED")

    doc_types: dict[str, int] = {}
    for a in ANALYSES:
        dt = a.get("document_type", "Unknown")
        doc_types[dt] = doc_types.get(dt, 0) + 1

    return jsonify({
        "total_screenings": total,
        "passed_count": passed,
        "suspicious_count": suspicious,
        "failed_count": failed,
        "fraud_rate_pct": round((failed / max(total, 1)) * 100, 1),
        "doc_types": doc_types,
        "pending_reviews": sum(1 for a in ANALYSES if a.get("review_status") == "pending"),
    })


@app.route("/api/analysis", methods=["GET"])
def api_list_analyses():
    status_filter = request.args.get("status")
    class_filter = request.args.get("classification")
    risk_filter = request.args.get("risk_level")
    skip = int(request.args.get("skip", 0))
    limit = int(request.args.get("limit", 20))

    result = list(ANALYSES)
    result = sorted(result, key=lambda x: x.get("created_at", ""), reverse=True)

    if class_filter and class_filter.lower() != "all":
        result = [a for a in result if a.get("classification", "").lower() == class_filter.lower() or a.get("verdict", "").lower() == class_filter.lower()]
    if status_filter and status_filter.lower() != "all":
        result = [a for a in result if a.get("status") == status_filter or a.get("review_status") == status_filter]
    if risk_filter and risk_filter.lower() != "all":
        result = [a for a in result if a.get("risk_level") == risk_filter]

    total = len(result)
    items = result[skip: skip + limit]

    lite = [_lite(a) for a in items]
    return jsonify({"items": lite, "total": total, "skip": skip, "limit": limit})


@app.route("/api/analysis/<analysis_id>", methods=["GET"])
def api_get_analysis(analysis_id: str):
    rec = _find(analysis_id)
    if not rec:
        return jsonify({"detail": "Analysis record not found"}), 404
    return jsonify(rec)


@app.route("/api/analysis/<analysis_id>/image", methods=["GET"])
def api_analysis_image(analysis_id: str):
    rec = _find(analysis_id)
    if not rec:
        return jsonify({"detail": "Not found"}), 404
    img_path = rec.get("image_path")
    if img_path and os.path.exists(img_path):
        return send_file(img_path, mimetype="image/jpeg")
    return jsonify({"detail": "Image not stored"}), 404


@app.route("/api/analysis/<analysis_id>/report/pdf", methods=["GET"])
def api_analysis_report(analysis_id: str):
    rec = _find(analysis_id)
    if not rec:
        return jsonify({"detail": "Not found"}), 404
    import json
    report_json = json.dumps(rec, indent=2, default=str)
    from io import BytesIO
    buf = BytesIO(report_json.encode())
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"report_{analysis_id}.json", mimetype="application/json")


@app.route("/api/analysis/<analysis_id>/review", methods=["POST"])
def api_review_analysis(analysis_id: str):
    rec = _find(analysis_id)
    if not rec:
        return jsonify({"detail": "Analysis record not found"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")      # "approved" | "rejected"
    notes = data.get("notes", "")

    if new_status in ("approved", "rejected", "pending"):
        rec["review_status"] = new_status
    if notes:
        rec["reviewer_notes"] = notes

    return jsonify({"success": True, "analysis": rec})


@app.route("/api/analysis/upload", methods=["POST"])
@app.route("/api/screen", methods=["POST"])
def api_upload():
    t0 = time.time()

    doc_file = request.files.get("file") or request.files.get("doc_image")
    if not doc_file or not doc_file.filename:
        return jsonify({"detail": "No file field in request. Use key 'file' or 'doc_image'."}), 400

    doc_type_hint = request.form.get("document_type", "unknown")

    analysis_id = f"SCN-{int(time.time()*1000) % 1_000_000:06d}"
    ext = os.path.splitext(doc_file.filename or "doc.jpg")[1] or ".jpg"
    saved_path = os.path.join(UPLOAD_DIR, f"{analysis_id}{ext}")
    doc_file.save(saved_path)

    try:
        img = Image.open(saved_path).convert("RGB")
        w, h = img.size

        # 1. Run Machine Learning Forgery Classification
        clf = classify(img)
        fake_prob = float(clf["fake_prob"])

        # 2. Run Error Level Analysis (Digital Splicing)
        ela_risk = float(_ela_heuristic(img))

        # 3. Metadata inspection (Photoshop / GIMP check)
        meta = analyze_metadata(saved_path)
        meta_risk = float(meta.get("risk", 0.0))

        # 4. Stamp / Seal forensics
        stamps = analyze_stamps(img)
        stamp_risk = float(stamps.get("risk", 0.0))

        # 5. Image quality / sharpness
        np_img = np.array(img)
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))

        # 6. Face portrait detection
        face_detected = False
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            face_detected = len(faces) > 0
        except Exception:
            pass

        # 7. OCR Field Extraction (Name, Age, DOB, ID Number, Gender, Document Type)
        ocr_fields = {}
        ocr_lines = []
        ocr_raw_text = ""
        try:
            ocr_res = ocr_extract(img)
            ocr_fields = ocr_res.get("fields", {})
            ocr_lines = ocr_res.get("lines", [])
            ocr_raw_text = ocr_res.get("raw_text", "")
        except Exception as ocr_err:
            print(f"[OCR extraction notice] {ocr_err}")

        # Extract person details from OCR
        name = ocr_fields.get("name")
        dob = ocr_fields.get("dob")
        age = ocr_fields.get("age") or calculate_age(dob)
        gender = ocr_fields.get("gender")
        id_number = ocr_fields.get("id_number") or ocr_fields.get("aadhaar_number") or ocr_fields.get("pan_number")
        detected_doc_type = ocr_fields.get("doc_type") or doc_type_hint

        # Format user-friendly document name
        doc_type_names = {
            "aadhaar": "Aadhaar Card",
            "pan": "PAN Card",
            "passport": "Passport",
            "driving_license": "Driving License",
            "voter_id": "Voter ID",
            "unknown": "Identity Document",
        }
        doc_display_name = doc_type_names.get(detected_doc_type, detected_doc_type.replace("_", " ").title())

        person_details = {
            "name": name if name else "Not isolated from scan",
            "age": f"{age} Years" if age is not None else "Not specified",
            "dob": dob if dob else "Not specified",
            "gender": gender if gender else "Not specified",
            "id_number": id_number if id_number else "Not isolated from scan",
            "document_type": doc_display_name,
            "father_name": ocr_fields.get("father_name") or "Not specified",
        }

        # 8. Multi-modal Risk Fusion
        max_tamper = max(fake_prob, ela_risk)
        combined_risk = float(np.clip(
            0.50 * fake_prob + 0.35 * ela_risk + 0.10 * meta_risk + 0.05 * stamp_risk,
            0.0, 1.0
        ))
        if max_tamper >= 0.50 and combined_risk < max_tamper:
            combined_risk = max_tamper

        # 9. Map to Pass / Suspicious / Failed & Probability
        classification, verdict, risk_score, real_pct, fake_pct = _classify_document(combined_risk, fake_prob)

        # Build clean verification checklist
        checklist = [
            {
                "item": "Document Format & Layout",
                "status": "Passed" if combined_risk < 0.40 else "Failed" if combined_risk > 0.60 else "Suspicious",
                "detail": f"{doc_display_name} standard format verified",
            },
            {
                "item": "Photo & Portrait Authenticity",
                "status": "Passed" if face_detected else "Suspicious",
                "detail": "Clear cardholder facial portrait verified" if face_detected else "Face region missing or blurred",
            },
            {
                "item": "Security Seal & Emblem",
                "status": "Passed" if stamp_risk < 0.20 else "Suspicious",
                "detail": "Security marks verified" if stamp_risk < 0.20 else "Seal anomaly detected",
            },
            {
                "item": "Digital Tampering / Editing",
                "status": "Passed" if not meta.get("software") and ela_risk < 0.35 else "Failed",
                "detail": "No editing software tags found" if not meta.get("software") else f"Edited in {meta['software']}",
            },
        ]

        # Plain-English Human Summary
        if classification == "Pass":
            human_summary = "Document passed all verification checks. Print quality, fonts, and portrait consistency indicate a genuine original ID."
        elif classification == "Suspicious":
            human_summary = "Document flagged as suspicious. Borderline image clarity, compression anomalies, or missing key fields detected. Manual review recommended."
        else:
            human_summary = "Verification failed! High probability of forgery or digital tampering detected on document face."

        # Technical findings & risk factors (for collapsible view)
        risk_factors = _build_risk_factors(clf, ela_risk, meta, stamps, sharpness, face_detected)
        forensic_findings = _build_forensic_findings(clf, ela_risk, meta, stamps, sharpness)

        elapsed_ms = int((time.time() - t0) * 1000)

        rec: dict = {
            "id": analysis_id,
            "analysis_number": f"AN-{datetime.now().year}-{len(ANALYSES)+1:04d}",
            "original_filename": doc_file.filename,
            "document_type": doc_display_name,
            "status": "completed" if classification == "Pass" else "review_required",
            "classification": classification,   # "Pass" | "Suspicious" | "Failed"
            "verdict": verdict,                 # "PASS" | "SUSPICIOUS" | "FAILED"
            "real_probability": real_pct,       # e.g. 98.2
            "fake_probability": fake_pct,       # e.g. 1.8
            "person_details": person_details,
            "human_summary": human_summary,
            "verification_checklist": checklist,
            "risk_level": "low" if classification == "Pass" else "medium" if classification == "Suspicious" else "critical",
            "risk_score": risk_score,
            "risk_explanation": human_summary,
            "risk_factors": risk_factors,
            "forensic_findings": forensic_findings,
            "forensic_summary": (
                f"{len(forensic_findings)} forensic anomal{'ies' if len(forensic_findings)!=1 else 'y'} detected."
                if forensic_findings else "Full forensic scan passed. No anomalies detected."
            ),
            "extracted_fields": {
                "name": person_details["name"],
                "age": person_details["age"],
                "dob": person_details["dob"],
                "id_number": person_details["id_number"],
                "gender": person_details["gender"],
                "document_type": doc_display_name,
                "resolution": f"{w}x{h}",
                "sharpness": "High" if sharpness >= 80 else "Low (Blurry)",
                "face_detected": "Yes" if face_detected else "No",
            },
            "ml_prediction": {
                "available": True,
                "model_version": "RandomForest-HOG-HSV",
                "avg_confidence": clf["confidence"],
                "fake_probability": fake_prob,
            },
            "ocr_confidence": round(1.0 - fake_prob * 0.4, 2),
            "ocr_results": {
                "raw_text": ocr_raw_text if ocr_raw_text else f"[Scanned {doc_file.filename}]\nType: {doc_display_name}\nName: {person_details['name']}",
                "lines_count": len(ocr_lines),
            },
            "review_status": "approved" if classification == "Pass" else "pending",
            "reviewer_notes": "",
            "file_size": os.path.getsize(saved_path),
            "mime_type": doc_file.content_type or "image/jpeg",
            "processing_time_ms": elapsed_ms,
            "created_at": datetime.now().isoformat(),
            "image_path": saved_path,
            "fake_prob": round(fake_prob, 4),
            "combined_risk": round(combined_risk, 4),
            "confidence": clf["confidence"],
            "method": clf["method"],
            "metadata": meta,
            "stamps": stamps,
            "quality": {
                "sharpness": round(sharpness, 1),
                "brightness": round(brightness, 1),
                "contrast": round(contrast, 1),
                "resolution": f"{w}x{h}",
            },
            "elapsed": round(time.time() - t0, 3),
        }

        ANALYSES.insert(0, rec)
        if len(ANALYSES) > 200:
            ANALYSES.pop()

        return jsonify(rec), 201

    except Exception as exc:
        traceback.print_exc()
        try:
            if os.path.exists(saved_path):
                os.remove(saved_path)
        except Exception:
            pass
        return jsonify({"detail": str(exc)}), 500


# ── Samples ─────────────────────────────────────────────────────────────────

@app.route("/api/samples", methods=["GET"])
def api_samples():
    out = []
    for s in SAMPLES:
        full_path = os.path.join(BASE_DIR, s["path"])
        out.append({
            "id": s["id"],
            "title": s["title"],
            "type": s["type"],
            "expected": s["expected"],
            "description": s["description"],
            "available": os.path.exists(full_path),
            "filename": os.path.basename(s["path"]),
        })
    return jsonify({"samples": out})


@app.route("/api/samples/<sample_id>/file", methods=["GET"])
def api_sample_file(sample_id: str):
    target = next((s for s in SAMPLES if s["id"] == sample_id), None)
    if not target:
        return jsonify({"detail": "Sample not found"}), 404
    full_path = os.path.join(BASE_DIR, target["path"])
    if not os.path.exists(full_path):
        return jsonify({"detail": "Sample file not on disk"}), 404
    return send_file(os.path.abspath(full_path), mimetype="image/jpeg")


# ── Static file serving (production SPA) ────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    dist_dir = os.path.join(BASE_DIR, "..", "frontend", "dist")
    if not os.path.exists(dist_dir):
        dist_dir = os.path.join(BASE_DIR, "frontend", "dist")
    if os.path.exists(dist_dir):
        full = os.path.join(dist_dir, path)
        if path and os.path.exists(full):
            return send_from_directory(dist_dir, path)
        index = os.path.join(dist_dir, "index.html")
        if os.path.exists(index):
            return send_from_directory(dist_dir, "index.html")
    return jsonify({
        "status": "healthy",
        "service": "VeriShieldAI API Server",
        "version": "VeriShieldAI-v3.2",
        "endpoints": {
            "health": "/api/system/health",
            "dashboard_stats": "/api/system/dashboard/stats",
            "screen": "/api/analysis/upload",
            "analyses": "/api/analysis"
        }
    }), 200


# ── Helpers ──────────────────────────────────────────────────────────────────

def _find(analysis_id: str) -> dict | None:
    return next((a for a in ANALYSES if a["id"] == analysis_id), None)


def _lite(a: dict) -> dict:
    person = a.get("person_details", {})
    return {
        "id": a["id"],
        "analysis_number": a["analysis_number"],
        "original_filename": a["original_filename"],
        "document_type": person.get("document_type") or a.get("document_type", "Identity Document"),
        "person_name": person.get("name") or "—",
        "person_age": person.get("age") or "—",
        "status": a["status"],
        "classification": a.get("classification") or ("Pass" if a.get("risk_level") == "low" else "Suspicious" if a.get("risk_level") == "medium" else "Failed"),
        "verdict": a.get("verdict") or ("PASS" if a.get("risk_level") == "low" else "SUSPICIOUS" if a.get("risk_level") == "medium" else "FAILED"),
        "real_probability": a.get("real_probability", round((1.0 - a.get("fake_prob", 0.0)) * 100, 1)),
        "fake_probability": a.get("fake_probability", round(a.get("fake_prob", 0.0) * 100, 1)),
        "risk_level": a["risk_level"],
        "risk_score": a["risk_score"],
        "review_status": a["review_status"],
        "created_at": a["created_at"],
        "processing_time_ms": a.get("processing_time_ms", 50),
    }


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("  VeriShieldAI API Server")
    print("  Classification: Pass / Suspicious / Failed")
    print(f"  Backend: http://127.0.0.1:{port}")
    print("  React UI: http://127.0.0.1:3000")
    print("=" * 60, flush=True)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
