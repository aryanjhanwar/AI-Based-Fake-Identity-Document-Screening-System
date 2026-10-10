"""Module 1 - Document forgery / tampering detection (pretrained ViT + ELA CNN)."""

from __future__ import annotations

import warnings

import numpy as np
import torch
from PIL import Image

from modules.models import DEVICE, ela_blend, get_forge_ela_cnn, get_forge_vit

warnings.filterwarnings("ignore")

_IMG = (224, 224)


def _vit_predict(pil_img: Image.Image):
    """ELA-blended ViT (zodumair). Returns forged probability in [0,1]."""
    model, proc = get_forge_vit()
    blended = ela_blend(pil_img)
    inp = proc(images=[blended], return_tensors="pt")
    inp = {k: (v.to(DEVICE) if DEVICE == "cuda" else v) for k, v in inp.items()}
    with torch.no_grad():
        logits = model(**inp).logits
    probs = torch.softmax(logits, dim=-1)[0].cpu().numpy()
    # label order: {0: 'real', 1: 'forged'}
    forged = float(probs[1]) if probs.shape[0] > 1 else float(probs[0])
    return forged


def _ela_cnn_predict(pil_img: Image.Image):
    """Dual RGB+ELA CNN (salmanzaman, CASIA v2) second opinion."""
    model = get_forge_ela_cnn()
    import tensorflow as tf

    def _ela(im: Image.Image, q=90, scale=15):
        import io

        from PIL import ImageChops, ImageEnhance

        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q)
        buf.seek(0)
        d = ImageEnhance.Brightness(ImageChops.difference(im, Image.open(buf).convert("RGB"))).enhance(scale)
        out = io.BytesIO()
        d.save(out, "JPEG", quality=75)
        x = tf.image.resize(tf.image.decode_jpeg(out.getvalue(), channels=3), _IMG)
        return (tf.cast(x, tf.float32) / 255.0).numpy()

    rgb = np.array(pil_img.resize(_IMG, Image.LANCZOS), np.float32)[np.newaxis] / 255.0
    pred = float(model.predict([rgb, _ela(pil_img)[np.newaxis]], verbose=0)[0][0])
    return pred


import joblib
import cv2
import pathlib

_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
FAST_MODEL_PATH = _BACKEND_DIR / "artifacts" / "fast_classifier.pkl"
_fast_model = None

def _load_fast_model():
    global _fast_model
    if _fast_model is not None:
        return _fast_model
    if FAST_MODEL_PATH.exists():
        _fast_model = joblib.load(FAST_MODEL_PATH)
    return _fast_model

def _extract_fast_features(img: Image.Image, size=(128, 128)):
    # Convert PIL RGB to CV2 BGR
    cv2_img = np.array(img.convert("RGB"))[:, :, ::-1].copy()
    img_resized = cv2.resize(cv2_img, size)
    
    # 1. Color Histogram (HSV)
    hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    hist_features = hist.flatten()
    
    # 2. HOG features
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    hog = cv2.HOGDescriptor(
        _winSize=(size[0], size[1]),
        _blockSize=(16, 16),
        _blockStride=(8, 8),
        _cellSize=(8, 8),
        _nbins=9
    )
    hog_features = hog.compute(gray).flatten()
    return np.concatenate([hist_features, hog_features])


def analyze_document(pil_img: Image.Image) -> dict:
    """Run document-level forgery screening. Uses fast Random Forest by default."""
    fast_model = _load_fast_model()
    
    if fast_model is not None:
        # FAST PATH (takes < 0.1 seconds)
        features = _extract_fast_features(pil_img)
        probs = fast_model.predict_proba([features])[0]
        # label 0 = Original, label 1 = Fake
        forge_prob = float(probs[1])
        risk = float(np.clip((forge_prob - 0.5) * 2.0, 0.0, 1.0)) if forge_prob >= 0.5 else 0.0
        verdict = "FORGED" if forge_prob >= 0.5 else "AUTHENTIC"
        
        return {
            "forge_probability": round(forge_prob, 4),
            "verdict": verdict,
            "risk": round(risk, 4),
            "models": {
                "fast_rf_classifier": round(forge_prob, 4)
            }
        }
        
    # SLOW PATH (Fallback to heavy models if PKL is missing)
    def _to_pil(img):
        return img.convert("RGB") if isinstance(img, Image.Image) else Image.open(img).convert("RGB")

    img = _to_pil(pil_img)
    
    forge_prob = None
    try:
        forge_prob = _vit_predict(img)
    except Exception as e:
        try:
            from modules.models import ela_residual_stats
            stats = ela_residual_stats(img)
            p95 = stats["ela_p95"]
            heuristic = (p95 - 30.0) / 50.0
            forge_prob = float(np.clip(heuristic, 0.0, 1.0))
        except Exception:
            pass

    ela_cnn_prob = None
    try:
        from config import MODELS
        if MODELS["forge_ela_cnn"]["enabled"]:
            ela_cnn_prob = float(_ela_cnn_predict(img))
    except Exception:
        pass

    if forge_prob is not None and ela_cnn_prob is not None:
        combined = 0.6 * forge_prob + 0.4 * ela_cnn_prob
    elif forge_prob is not None:
        combined = forge_prob
    elif ela_cnn_prob is not None:
        combined = ela_cnn_prob
    else:
        combined = 0.0

    combined = float(np.clip(combined, 0.0, 1.0))
    risk = float(np.clip((combined - 0.5) * 2.0, 0.0, 1.0)) if combined >= 0.5 else 0.0
    verdict = "FORGED" if combined >= 0.5 else "AUTHENTIC"
    return {
        "forge_probability": round(combined, 4),
        "verdict": verdict,
        "risk": round(risk, 4),
        "models": {
            "vit_ela_blend": round(forge_prob, 4) if forge_prob is not None else None,
            "ela_cnn_casia2": round(ela_cnn_prob, 4) if ela_cnn_prob is not None else None,
        },
    }