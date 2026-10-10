"""
Train EfficientNet-B0 to classify ID documents as REAL or FAKE.
Dataset layout:
  Dataset/
    Aadhar/Original/*.jpg   → label 0 (real)
    Aadhar/Fake/*.jpg       → label 1 (fake)
    PAN/Original/*.jpg
    PAN/Fake/*.jpg
    Passport/Original/*.jpg
    Passport/Fake/*.jpg

Run: python scripts/train_classifier.py
Output: artifacts/id_classifier.pth
"""

from __future__ import annotations
import os, sys, json, time, pathlib, random
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from sklearn.model_selection import train_test_split
from PIL import Image

# ── config ───────────────────────────────────────────────────────────────────
DATASET_ROOT = pathlib.Path("Dataset")
OUT_DIR      = pathlib.Path("artifacts")
OUT_DIR.mkdir(exist_ok=True)
MODEL_OUT    = OUT_DIR / "id_classifier.pth"
BATCH        = 32
EPOCHS       = 15
LR           = 3e-4
IMG_SIZE     = 224
SEED         = 42

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

TRAIN_TF = transforms.Compose([
    transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
    transforms.RandomCrop(IMG_SIZE),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
VAL_TF = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

class IDDataset(Dataset):
    def __init__(self, paths, labels, tf):
        self.paths, self.labels, self.tf = paths, labels, tf
    def __len__(self): return len(self.paths)
    def __getitem__(self, i):
        try:
            img = Image.open(self.paths[i]).convert("RGB")
            return self.tf(img), self.labels[i]
        except Exception:
            img = Image.new("RGB", (IMG_SIZE, IMG_SIZE))
            return self.tf(img), self.labels[i]

def main():
    print(f"[train] Using device: {DEVICE}")
    if DEVICE == "cuda":
        print(f"[train] GPU: {torch.cuda.get_device_name(0)}")

    samples: list[tuple[str, int]] = []
    for doc in ("Aadhar", "PAN", "Passport"):
        for label, folder in ((0, "Original"), (1, "Fake")):
            p = DATASET_ROOT / doc / folder
            if not p.exists():
                continue
            for f in p.iterdir():
                if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    samples.append((str(f), label))

    random.shuffle(samples)
    paths  = [s[0] for s in samples]
    labels = [s[1] for s in samples]
    print(f"[train] Total: {len(samples)} images  (real={labels.count(0)}, fake={labels.count(1)})")

    X_train, X_val, y_train, y_val = train_test_split(
        paths, labels, test_size=0.15, stratify=labels, random_state=SEED
    )
    print(f"[train] Train={len(X_train)}  Val={len(X_val)}")

    class_counts = [y_train.count(0), y_train.count(1)]
    weights = [1.0 / class_counts[l] for l in y_train]
    sampler = WeightedRandomSampler(weights, len(weights))

    train_ds = IDDataset(X_train, y_train, TRAIN_TF)
    val_ds   = IDDataset(X_val,   y_val,   VAL_TF)
    train_dl = DataLoader(train_ds, batch_size=BATCH, sampler=sampler, num_workers=0, pin_memory=(DEVICE=="cuda"))
    val_dl   = DataLoader(val_ds,   batch_size=BATCH, shuffle=False,   num_workers=0, pin_memory=(DEVICE=="cuda"))

    model = models.efficientnet_b0(weights=None)
    _url = "https://download.pytorch.org/models/efficientnet_b0_rwightman-7f5810bc.pth"
    state_dict = torch.hub.load_state_dict_from_url(_url, progress=True, check_hash=False)
    model.load_state_dict(state_dict)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model = model.to(DEVICE)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    n_real, n_fake = labels.count(0), labels.count(1)
    pos_weight = torch.tensor([n_real / max(n_fake, 1)], device=DEVICE)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor([1.0, pos_weight.item()], device=DEVICE))

    best_val_acc = 0.0
    history = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0
        t0 = time.time()
        for imgs, lbls in train_dl:
            imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, lbls)
            loss.backward()
            optimizer.step()
            train_loss  += loss.item() * imgs.size(0)
            preds = out.argmax(1)
            train_correct += (preds == lbls).sum().item()
            train_total   += imgs.size(0)
        scheduler.step()

        model.eval()
        val_correct, val_total, val_loss = 0, 0, 0.0
        with torch.no_grad():
            for imgs, lbls in val_dl:
                imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE)
                out = model(imgs)
                loss = criterion(out, lbls)
                val_loss += loss.item() * imgs.size(0)
                preds = out.argmax(1)
                val_correct += (preds == lbls).sum().item()
                val_total   += imgs.size(0)

        tr_acc  = train_correct / train_total
        val_acc = val_correct   / val_total
        elapsed = time.time() - t0
        history.append({"epoch": epoch, "train_acc": round(tr_acc,4), "val_acc": round(val_acc,4)})
        print(f"Epoch {epoch:02d}/{EPOCHS}  train_acc={tr_acc:.3f}  val_acc={val_acc:.3f}  time={elapsed:.1f}s")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({"model_state": model.state_dict(), "classes": ["real","fake"], "val_acc": val_acc}, MODEL_OUT)
            print(f"  > Saved best model (val_acc={val_acc:.3f})")

    print(f"\n[train] Done. Best val_acc={best_val_acc:.3f}  Saved to {MODEL_OUT}")
    with open(OUT_DIR / "train_history.json", "w") as f:
        json.dump(history, f, indent=2)

if __name__ == "__main__":
    main()
