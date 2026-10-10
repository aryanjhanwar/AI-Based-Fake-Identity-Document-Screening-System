"""
Core ID document classifier — loads the trained EfficientNet-B0 and runs inference.
Falls back to heuristic ELA if no model is trained yet.
"""
from __future__ import annotations
import pathlib, re, io
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import joblib
import cv2

_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
MODEL_PATH = _BACKEND_DIR / "artifacts" / "id_classifier.pth"

_model = None
_device = "cpu"

def _load_model():
    global _model, _device
    if _model is not None:
        return _model
    import torch
    from torchvision import models, transforms
    import torch.nn as nn

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    if not MODEL_PATH.exists():
        return None

    ckpt = torch.load(MODEL_PATH, map_location=_device)
    m = models.efficientnet_b0(weights=None)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, 2)
    m.load_state_dict(ckpt["model_state"])
    m.eval().to(_device)
    _model = m
    print(f"[classifier] Loaded model from {MODEL_PATH}  val_acc={ckpt.get('val_acc','?')}")
    return _model


def _ela_heuristic(img: Image.Image) -> float:
    """Error Level Analysis heuristic — returns fake probability in [0,1]."""
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    buf.seek(0)
    diff = ImageChops.difference(img, Image.open(buf).convert("RGB"))
    ela = ImageEnhance.Brightness(diff).enhance(15)
    arr = np.asarray(ela.convert("L"), dtype=np.float32)
    p95 = float(np.percentile(arr, 95))
    mean = float(arr.mean())
    # Images with uniform high ELA = printed original; spiked local ELA = manipulation
    score = np.clip((p95 - 35.0) / 60.0, 0.0, 1.0)
    return float(score)


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


def predict(img: Image.Image) -> dict:
    """
    Returns:
        label:       'REAL' | 'FAKE'
        confidence:  float 0..1
        fake_prob:   float 0..1 (probability document is fake)
        method:      'model' | 'ela_heuristic'
    """
    import torch
    from torchvision import transforms

    # 1. Try Fast ML Model first
    fast_model = _load_fast_model()
    if fast_model is not None:
        features = _extract_fast_features(img)
        probs = fast_model.predict_proba([features])[0]
        # label 0 = Original, label 1 = Fake
        fake_prob = float(probs[1])
        label = "FAKE" if fake_prob >= 0.5 else "REAL"
        return {
            "label": label, 
            "fake_prob": round(fake_prob, 4),
            "confidence": round(float(max(probs)), 4), 
            "method": "fast_rf_classifier"
        }

    # 2. Try PyTorch Deep Learning Model
    model = _load_model()
    if model is not None:
        tf = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        x = tf(img.convert("RGB")).unsqueeze(0).to(_device)
        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        fake_prob = float(probs[1])
        label = "FAKE" if fake_prob >= 0.5 else "REAL"
        return {"label": label, "fake_prob": round(fake_prob, 4),
                "confidence": round(float(max(probs)), 4), "method": "model"}
    else:
        # Heuristic fallback
        fake_prob = _ela_heuristic(img)
        label = "FAKE" if fake_prob >= 0.5 else "REAL"
        return {"label": label, "fake_prob": round(fake_prob, 4),
                "confidence": round(max(fake_prob, 1 - fake_prob), 4), "method": "ela_heuristic"}
