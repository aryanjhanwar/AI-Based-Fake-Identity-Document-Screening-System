"""Adapter for the newly trained EfficientNet-B0 Document Forgery Detector."""

from PIL import Image
from modules.inference import predict_document
import os
import tempfile

def analyze_document(pil_img: Image.Image) -> dict:
    """Run document-level forgery screening using the new custom model."""
    
    # Save the PIL image temporarily because the inference module expects a path
    # (In a production rewrite, predict_document could be refactored to accept PIL images directly)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        pil_img.convert("RGB").save(tmp.name, "JPEG")
        temp_path = tmp.name

    try:
        # Run inference
        result = predict_document(temp_path)
        
        # Match the old API's structure so risk.py and app.py don't break
        forged_prob = result["calibrated_score"] if result["calibrated_score"] is not None else 0.0
        verdict = result["predicted_class"]
        
        # Calculate risk (0..1 scale, 0.5 is threshold)
        risk = float(max(0.0, min(1.0, (forged_prob - 0.5) * 2.0))) if verdict == "Forged" else 0.0
        
        return {
            "forge_probability": round(forged_prob, 4),
            "verdict": verdict.upper(), # 'AUTHENTIC' or 'FORGED'
            "risk": round(risk, 4),
            "models": {
                "efficientnet_b0_custom": round(forged_prob, 4),
                "status": result["input_validation_status"],
                "errors": result["inference_error"]
            },
        }
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
