import os
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# Inference configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CHECKPOINT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts", "forgery_detector", "efficientnet_b0_best.pth")
THRESHOLD = 0.50 # This should be calibrated later
MODEL_IDENTIFIER = "EfficientNet-B0 (Custom Fine-tuned)"
CLASS_MAP = {0: "Genuine", 1: "Forged"}

# Preprocessing must match Phase 6 exactly
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model
        
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"Model checkpoint not found at {CHECKPOINT_PATH}")
        
    try:
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, 2)
        
        checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE, weights_only=True)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(DEVICE)
        model.eval()
        _model = model
        return _model
    except Exception as e:
        raise RuntimeError(f"Failed to load model architecture or weights: {e}")

def predict_document(image_path: str, threshold: float = THRESHOLD) -> dict:
    """
    Run standalone inference on a single document image.
    Returns a structured dictionary with predictions, scores, and status.
    """
    result = {
        "predicted_class": None,
        "raw_forgery_score": None,
        "calibrated_score": None,
        "model_identifier": MODEL_IDENTIFIER,
        "threshold_used": threshold,
        "input_validation_status": "PENDING",
        "inference_error": None
    }
    
    # 1. Input Validation
    if not os.path.exists(image_path):
        result["input_validation_status"] = "INVALID"
        result["inference_error"] = "File does not exist."
        return result
        
    try:
        image = Image.open(image_path).convert("RGB")
        image.verify() # Fast check
        image = Image.open(image_path).convert("RGB") # Re-open after verify
        result["input_validation_status"] = "VALID"
    except Exception as e:
        result["input_validation_status"] = "CORRUPT"
        result["inference_error"] = f"Failed to open or verify image: {e}"
        return result
        
    # 2. Inference
    try:
        model = _load_model()
        
        input_tensor = preprocess(image).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            outputs = model(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)[0]
            
            # Index 1 is Forged
            forged_prob = probabilities[1].item()
            
            # Predict based on threshold
            predicted_idx = 1 if forged_prob >= threshold else 0
            
            result["raw_forgery_score"] = forged_prob
            result["calibrated_score"] = forged_prob # Can be updated with platt scaling later
            result["predicted_class"] = CLASS_MAP[predicted_idx]
            
    except Exception as e:
        result["inference_error"] = f"Inference execution failed: {e}"
        
    return result

if __name__ == "__main__":
    # Simple self-test
    import sys
    if len(sys.argv) > 1:
        test_img = sys.argv[1]
        print(f"Testing inference on {test_img}")
        res = predict_document(test_img)
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python inference.py <path_to_image>")
