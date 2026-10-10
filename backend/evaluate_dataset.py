import os
import glob
import time
from PIL import Image
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

from modules import forge_detector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_ROOT = os.path.join(BASE_DIR, "Dataset")

def evaluate_dataset(max_samples_per_class=5):
    print("Starting dataset evaluation...")
    
    categories = ["Aadhar", "PAN", "Passport"]
    classes = ["Original", "Fake"]
    
    total_images = 0
    correct_predictions = 0
    
    for category in categories:
        for cls in classes:
            dir_path = os.path.join(DATASET_ROOT, category, cls)
            if not os.path.exists(dir_path):
                print(f"Directory not found: {dir_path}")
                continue
                
            # Supported image formats
            images = []
            for ext in ('*.jpg', '*.jpeg', '*.png'):
                images.extend(glob.glob(os.path.join(dir_path, ext)))
                
            if not images:
                print(f"No images found in {dir_path}")
                continue
                
            # Limit samples to speed up evaluation for demonstration
            sample_images = images[:max_samples_per_class] if max_samples_per_class else images
            
            print(f"\nEvaluating {category} - {cls} (Testing {len(sample_images)} samples)")
            
            for img_path in sample_images:
                try:
                    img = Image.open(img_path).convert("RGB")
                    result = forge_detector.analyze_document(img)
                    
                    # cls is "Original" or "Fake"
                    # result["verdict"] is "AUTHENTIC" or "FORGED"
                    predicted_class = "Original" if result["verdict"] == "AUTHENTIC" else "Fake"
                    is_correct = (predicted_class == cls)
                    
                    total_images += 1
                    if is_correct:
                        correct_predictions += 1
                        
                    print(f"  [ {'PASS' if is_correct else 'FAIL'} ] File: {os.path.basename(img_path)} | Predicted: {predicted_class} | Score: {result['forge_probability']}")
                except Exception as e:
                    print(f"  [ ERROR ] Failed to process {os.path.basename(img_path)}: {e}")

    if total_images > 0:
        accuracy = (correct_predictions / total_images) * 100
        print(f"\nEvaluation Complete!")
        print(f"Total Evaluated: {total_images}")
        print(f"Correct Predictions: {correct_predictions}")
        print(f"Accuracy: {accuracy:.2f}%")
    else:
        print("No images were evaluated.")

if __name__ == "__main__":
    # Test on a small subset first (5 from each class)
    evaluate_dataset(max_samples_per_class=5)
