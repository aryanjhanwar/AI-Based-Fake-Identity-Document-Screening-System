import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import time

# Configurations
SEED = 42
BATCH_SIZE = 16
MAX_EPOCHS = 15
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MANIFEST_PATH = "splits_manifest.json"
ARTIFACTS_DIR = "artifacts/forgery_detector"

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# Set seeds for reproducibility
torch.manual_seed(SEED)
np.random.seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

class DocumentDataset(Dataset):
    def __init__(self, split_data, transform=None):
        self.data = split_data
        self.transform = transform
        self.class_map = {"Genuine": 0, "Forged": 1}

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        img_path = item["path"]
        label = self.class_map[item["class"]]

        try:
            image = Image.open(img_path).convert("RGB")
        except Exception:
            # Fallback for corrupt images (should be 0 based on audit, but just in case)
            image = Image.new("RGB", (224, 224), (0, 0, 0))

        if self.transform:
            image = self.transform(image)

        return image, label

def get_transforms():
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomRotation(5),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    return train_transform, eval_transform

def load_data():
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
        
    train_transform, eval_transform = get_transforms()
    
    train_ds = DocumentDataset(manifest["train"], transform=train_transform)
    val_ds = DocumentDataset(manifest["val"], transform=eval_transform)
    test_ds = DocumentDataset(manifest["test"], transform=eval_transform)
    
    # Calculate class weights for training to handle imbalance
    class_counts = manifest["metadata"]["class_distribution"]["train"]
    total = class_counts["Genuine"] + class_counts["Forged"]
    weight_genuine = total / (2.0 * class_counts["Genuine"])
    weight_forged = total / (2.0 * class_counts["Forged"])
    class_weights = torch.tensor([weight_genuine, weight_forged], dtype=torch.float).to(DEVICE)
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    return train_loader, val_loader, test_loader, class_weights

def get_model(model_name="efficientnet_b0"):
    print(f"Loading {model_name}...")
    if model_name == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, 2)
    elif model_name == "resnet50":
        model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, 2)
    else:
        raise ValueError("Unsupported model")
        
    return model.to(DEVICE)

def evaluate(model, dataloader, criterion):
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
    epoch_loss = running_loss / len(dataloader.dataset)
    acc = accuracy_score(all_labels, all_preds)
    precision, recall, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average='macro', zero_division=0)
    
    return epoch_loss, acc, precision, recall, f1

def train_model():
    print(f"Using device: {DEVICE}")
    train_loader, val_loader, _, class_weights = load_data()
    
    model = get_model("efficientnet_b0")
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2)
    
    best_f1 = 0.0
    
    # Store metrics for logging
    history = []
    
    print("Starting training...")
    for epoch in range(MAX_EPOCHS):
        since = time.time()
        model.train()
        running_loss = 0.0
        
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            with torch.set_grad_enabled(True):
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
            running_loss += loss.item() * inputs.size(0)
            
        train_loss = running_loss / len(train_loader.dataset)
        val_loss, val_acc, val_precision, val_recall, val_f1 = evaluate(model, val_loader, criterion)
        
        scheduler.step(val_f1)
        
        time_elapsed = time.time() - since
        print(f"Epoch {epoch+1}/{MAX_EPOCHS} [{time_elapsed:.0f}s] - "
              f"Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f} - "
              f"Val Acc: {val_acc:.4f} - Val F1: {val_f1:.4f}")
              
        history.append({
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "val_f1": val_f1
        })
        
        if val_f1 > best_f1:
            best_f1 = val_f1
            checkpoint_path = os.path.join(ARTIFACTS_DIR, "efficientnet_b0_best.pth")
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': val_f1,
            }, checkpoint_path)
            print(f"  [*] Best checkpoint saved! (Val F1: {best_f1:.4f})")
            
    # Save metadata
    with open(os.path.join(ARTIFACTS_DIR, "training_history.json"), "w") as f:
        json.dump(history, f, indent=4)
        
    print("Training complete. Best Validation F1:", best_f1)

if __name__ == "__main__":
    train_model()
