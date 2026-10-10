import os
import json
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score
import numpy as np

# Use the components we already built
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scripts.train_model import DocumentDataset, get_transforms, get_model, DEVICE, ARTIFACTS_DIR

MANIFEST_PATH = "splits_manifest.json"
CHECKPOINT_PATH = os.path.join(ARTIFACTS_DIR, "efficientnet_b0_best.pth")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "evaluation_report.json")

def evaluate_on_test_set():
    print("Starting Phase 8: Independent Test Set Evaluation...")
    
    if not os.path.exists(CHECKPOINT_PATH):
        print(f"Error: Model checkpoint not found at {CHECKPOINT_PATH}. Train the model first.")
        return
        
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    _, eval_transform = get_transforms()
    test_ds = DocumentDataset(manifest["test"], transform=eval_transform)
    test_loader = DataLoader(test_ds, batch_size=16, shuffle=False, num_workers=0)
    
    # Load Model
    model = get_model("efficientnet_b0")
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE, weights_only=True)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    all_preds = []
    all_labels = []
    all_probs = []
    misclassified = []
    
    print("Running inference on test set...")
    with torch.no_grad():
        for i, (inputs, labels) in enumerate(test_loader):
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            outputs = model(inputs)
            probs = torch.softmax(outputs, dim=1)
            
            _, preds = torch.max(outputs, 1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs[:, 1].cpu().numpy()) # Probability of Forged
            
            # Track misclassifications
            batch_start_idx = i * 16
            for j in range(len(preds)):
                if preds[j] != labels[j]:
                    global_idx = batch_start_idx + j
                    img_path = manifest["test"][global_idx]["path"]
                    true_class = "Forged" if labels[j] == 1 else "Genuine"
                    pred_class = "Forged" if preds[j] == 1 else "Genuine"
                    prob_forged = probs[j, 1].item()
                    
                    misclassified.append({
                        "path": img_path,
                        "true_class": true_class,
                        "predicted_class": pred_class,
                        "forgery_probability": round(prob_forged, 4)
                    })

    # Metrics calculation
    acc = accuracy_score(all_labels, all_preds)
    precision, recall, f1, support = precision_recall_fscore_support(all_labels, all_preds)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(all_labels, all_preds, average='macro')
    
    # ROC AUC requires both classes present, usually true for test sets
    try:
        roc_auc = roc_auc_score(all_labels, all_probs)
    except Exception:
        roc_auc = None

    cm = confusion_matrix(all_labels, all_preds, labels=[0, 1])
    # cm[0][0] = TN (Genuine correctly identified)
    # cm[0][1] = FP (Genuine misclassified as Forged = False Rejection)
    # cm[1][0] = FN (Forged misclassified as Genuine = False Acceptance)
    # cm[1][1] = TP (Forged correctly identified)
    
    tn, fp, fn, tp = cm.ravel()
    
    total_genuine = tn + fp
    total_forged = fn + tp
    
    far = (fn / total_forged) if total_forged > 0 else 0.0 # False Acceptance Rate (Forged -> Genuine)
    frr = (fp / total_genuine) if total_genuine > 0 else 0.0 # False Rejection Rate (Genuine -> Forged)

    report = {
        "model": "EfficientNet-B0",
        "checkpoint": CHECKPOINT_PATH,
        "metrics": {
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "roc_auc": round(roc_auc, 4) if roc_auc else None,
            "false_acceptance_rate": round(far, 4),
            "false_rejection_rate": round(frr, 4),
        },
        "class_metrics": {
            "Genuine": {
                "precision": round(precision[0], 4),
                "recall": round(recall[0], 4),
                "f1": round(f1[0], 4),
                "support": int(support[0])
            },
            "Forged": {
                "precision": round(precision[1], 4),
                "recall": round(recall[1], 4),
                "f1": round(f1[1], 4),
                "support": int(support[1])
            }
        },
        "confusion_matrix": {
            "TN_Genuine_Correct": int(tn),
            "FP_Genuine_as_Forged": int(fp),
            "FN_Forged_as_Genuine": int(fn),
            "TP_Forged_Correct": int(tp)
        },
        "misclassifications": misclassified
    }

    with open(REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"\nEvaluation Complete! Report saved to {REPORT_PATH}")
    print(f"Accuracy: {acc:.2f} | Macro F1: {macro_f1:.2f}")
    print(f"False Acceptance Rate (FAR): {far:.2%} ({fn}/{total_forged})")
    print(f"False Rejection Rate (FRR): {frr:.2%} ({fp}/{total_genuine})")

if __name__ == "__main__":
    evaluate_on_test_set()
