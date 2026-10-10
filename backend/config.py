"""Central configuration: model registry, risk weights, thresholds, paths.

Standardized decisions come from thresholds here (single source of truth),
so checkpoints across an org produce identical verdicts.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MORPH_DIR = os.path.join(DATA_DIR, "morphed")
TRAIL_DIR = os.path.join(DATA_DIR, "audit_trails")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRAIL_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Low-memory & Device Configuration (Render 512MB RAM Optimization)
# ---------------------------------------------------------------------------
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_allocator_strategy", "naive")
os.environ.setdefault("FLAGS_fraction_of_cpu_memory_to_use", "0.15")
os.environ.setdefault("CPU_NUM", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

DEVICE = os.environ.get("DEVICE", "cpu")

# ---------------------------------------------------------------------------
# HF model registry (all PRETRAINED - nothing is trained from scratch)
# ---------------------------------------------------------------------------
MODELS = {
    # Document-level real/forged classifier (ViT-B/16 fine-tuned on
    # ELA-blended forged documents incl. stamp-overlay, copy-move, splicing).
    "forge_vit": {
        "repo": "zodumair/document-forgery-detector",
        "kind": "transformers",
    },
    # Dual-branch RGB + ELA CNN (CASIA v2), used as a second opinion.
    "forge_ela_cnn": {
        "repo": "salmanzaman777/digital-image-forgery-detection-model",
        "file": "M3_best_v2.h5",
        "kind": "keras",
        "enabled": bool(os.environ.get("FORGE_KERAS", "1") == "1"),
    },
    # Face detection + embeddings (VGGFace2). Not HF-hosted but pretrained.
    "face": {"backend": "facenet", "embedder": "InceptionResnetV1(vggface2)"},
    "ocr": {"repo": "PaddleOCR PP-OCRv5_mobile_det/rec", "lang": "en"},
}

# ELA preprocessing constants - must match zodumair training recipe
ELA_JPEG_QUALITY = 90
ELA_SCALE = 15
ELA_FINAL_JPEG_QUALITY = 75
ELA_BLEND_ALPHA = 0.3  # forged detector mixes original + ELA residual at 0.3

# ---------------------------------------------------------------------------
# Risk fusion weights (sum = 1.0)
# ---------------------------------------------------------------------------
RISK_WEIGHTS = {
    "forgery": 0.25,
    "stamp": 0.15,
    "metadata": 0.10,
    "face": 0.20,
    "ocr": 0.15,
    "validation": 0.15,
}

# A single high-confidence signal forces at least a manual review.
STRONG_SIGNAL_OVERRIDE = {
    "forgery": 0.85,  # forge prob above this => cannot be auto-PASS
    "stamp": 0.85,
    "metadata": 0.80,
    "face": 0.80,
    "ocr": 0.80,
    "validation": 0.85,
}

# ---------------------------------------------------------------------------
# Standardized verdict thresholds
# ---------------------------------------------------------------------------
VERDICT = {
    "pass": 0.34,
    "review": 0.66,  # above => reject; between pass and review => manual review
}

# ---------------------------------------------------------------------------
# Per-module thresholds
# ---------------------------------------------------------------------------
FACE_MATCH_THRESHOLD = 0.50  # cosine similarity (facenet space)
STAMP_MIN_CIRCULARITY = 0.55
STAMP_MIN_RADIUS_RATIO = 0.02  # of min(image w,h)
PASS_INDICATOR_TEXT = ("signature", "sign", "stamp", "seal")

# ---------------------------------------------------------------------------
# PaddleOCR settings
# ---------------------------------------------------------------------------

# Mobile detection/recognition models are substantially lighter than the
# server models while retaining support for English identity documents.
OCR_KWARGS = dict(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    lang="en",
    # PaddlePaddle 3.3.1 on Windows currently fails during inference with
    # oneDNN enabled, so keep the mobile models on the stable CPU path.
    enable_mkldnn=False,
)

# ---------------------------------------------------------------------------
# Metadata forensics heuristics
# ---------------------------------------------------------------------------
SUSPICIOUS_SOFTWARE = (
    "photoshop",
    "paint.net",
    "gimp",
    "adobe illustrator",
    "photoscape",
    "pixlr",
    "snapseed",
    "camscanner pro",
    "adobe acrobat pro",
    "picsart",
)
SCREENSHOT_SOFTWARE = ("snipping", "screen", "capture", "bandicam", "psd")