import os
import glob
import time
import numpy as np
import cv2
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

DATASET_ROOT = r"d:\Projects\sih-identity-screening-main\Dataset"
MODEL_OUTPUT_PATH = r"d:\Projects\sih-identity-screening-main\artifacts\fast_classifier.pkl"

def extract_features(img_path, size=(128, 128)):
    try:
        img = cv2.imread(img_path)
        if img is None:
            return None
        
        img = cv2.resize(img, size)
        
        # 1. Color Histogram (HSV)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        hist_features = hist.flatten()
        
        # 2. HOG features
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hog = cv2.HOGDescriptor(
            _winSize=(size[0], size[1]),
            _blockSize=(16, 16),
            _blockStride=(8, 8),
            _cellSize=(8, 8),
            _nbins=9
        )
        hog_features = hog.compute(gray).flatten()
        
        # Combine features
        combined = np.concatenate([hist_features, hog_features])
        return combined
    except Exception as e:
        print(f"Error extracting features from {img_path}: {e}")
        return None

def train_and_save():
    print("Extracting features from dataset...")
    categories = ["Aadhar", "PAN", "Passport"]
    classes = ["Original", "Fake"]
    
    X = []
    y = []
    
    for category in categories:
        for cls in classes:
            dir_path = os.path.join(DATASET_ROOT, category, cls)
            if not os.path.exists(dir_path):
                print(f"Skipping missing directory: {dir_path}")
                continue
                
            images = []
            for ext in ('*.jpg', '*.jpeg', '*.png'):
                images.extend(glob.glob(os.path.join(dir_path, ext)))
                
            print(f"Processing {category}/{cls} ({len(images)} images)...")
            
            # Label: 0 for Original, 1 for Fake
            label = 0 if cls == "Original" else 1
            
            for img_path in images:
                features = extract_features(img_path)
                if features is not None:
                    X.append(features)
                    y.append(label)
                    
    if len(X) == 0:
        print("No valid images found to train.")
        return
        
    X = np.array(X)
    y = np.array(y)
    
    print(f"\nExtracted {X.shape[1]} features for {X.shape[0]} samples.")
    print("Training RandomForestClassifier...")
    
    # Needs at least 2 samples to split
    if len(X) > 1:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    else:
        X_train, X_test, y_train, y_test = X, X, y, y
        
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    
    t0 = time.time()
    clf.fit(X_train, y_train)
    t1 = time.time()
    print(f"Training completed in {t1-t0:.2f} seconds.")
    
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nValidation Accuracy: {acc * 100:.2f}%")
    print("Classification Report:")
    try:
        print(classification_report(y_test, y_pred, target_names=["Original", "Fake"]))
    except Exception as e:
        print("Could not print classification report (possibly only one class present).")
    
    # Save the model
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_OUTPUT_PATH)
    print(f"\nModel successfully saved to {MODEL_OUTPUT_PATH}")

if __name__ == "__main__":
    train_and_save()
