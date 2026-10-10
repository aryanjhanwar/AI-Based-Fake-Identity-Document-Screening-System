import os
import glob
import json
import hashlib
import random
import re
from collections import defaultdict

def get_image_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest()
    except Exception:
        return None

def extract_group_id(filepath):
    """
    Extract a base group ID from the filename to prevent data leakage 
    (e.g., original and augmented/tampered versions of the same document).
    """
    basename = os.path.basename(filepath)
    name, _ = os.path.splitext(basename)
    
    # Strip Roboflow suffixes (e.g. .rf.hash)
    name = re.sub(r'\.rf\.[a-z0-9]+$', '', name)
    name = re.sub(r'_jpg$', '', name)
    name = re.sub(r'_png$', '', name)
    
    # Strip common fake/morphed prefixes or suffixes
    name = re.sub(r'^fake_0_', '', name)
    name = re.sub(r'^0_', '', name)
    name = re.sub(r'-1-$', '', name)
    name = re.sub(r'-2-$', '', name)
    
    return name

def create_splits(dataset_roots, output_json="splits_manifest.json", seed=42):
    random.seed(seed)
    print("Extracting images and determining groups...")
    
    image_hashes = {}
    groups = defaultdict(list)
    class_distribution = {"Genuine": 0, "Forged": 0}
    
    # Collect deduplicated images
    for source_name, root_dir in dataset_roots.items():
        if not os.path.exists(root_dir):
            continue
            
        for ext in ('**/*.jpg', '**/*.jpeg', '**/*.png', '**/*.webp'):
            for filepath in glob.iglob(os.path.join(root_dir, ext), recursive=True):
                file_hash = get_image_hash(filepath)
                if not file_hash or file_hash in image_hashes:
                    continue  # Skip exact duplicates
                    
                image_hashes[file_hash] = filepath
                
                path_parts = filepath.split(os.sep)
                img_class = "Genuine" if ("Original" in path_parts or "aadhar_labeled_imgs" in path_parts) else "Forged"
                
                group_id = extract_group_id(filepath)
                groups[group_id].append({
                    "path": filepath,
                    "class": img_class,
                    "source": source_name
                })
    
    print(f"Total unique images: {len(image_hashes)}")
    print(f"Total distinct groups found: {len(groups)}")
    
    # Shuffle groups
    group_ids = list(groups.keys())
    random.shuffle(group_ids)
    
    # Splitting limits
    n_groups = len(group_ids)
    train_end = int(0.70 * n_groups)
    val_end = int(0.85 * n_groups)
    
    train_groups = group_ids[:train_end]
    val_groups = group_ids[train_end:val_end]
    test_groups = group_ids[val_end:]
    
    manifest = {
        "train": [],
        "val": [],
        "test": [],
        "metadata": {
            "seed": seed,
            "grouping_strategy": "Basename extraction and robust regex stripping",
            "counts": {"train": 0, "val": 0, "test": 0},
            "class_distribution": {"train": {"Genuine": 0, "Forged": 0}, "val": {"Genuine": 0, "Forged": 0}, "test": {"Genuine": 0, "Forged": 0}}
        }
    }
    
    def assign_split(g_ids, split_name):
        for gid in g_ids:
            for item in groups[gid]:
                manifest[split_name].append(item)
                manifest["metadata"]["counts"][split_name] += 1
                manifest["metadata"]["class_distribution"][split_name][item["class"]] += 1
                
    assign_split(train_groups, "train")
    assign_split(val_groups, "val")
    assign_split(test_groups, "test")
    
    with open(output_json, 'w') as f:
        json.dump(manifest, f, indent=4)
        
    print(f"Splits saved to {output_json}")
    for split in ["train", "val", "test"]:
        cnt = manifest["metadata"]["counts"][split]
        dist = manifest["metadata"]["class_distribution"][split]
        print(f" - {split.upper()}: {cnt} images | Genuine: {dist['Genuine']} | Forged: {dist['Forged']}")

if __name__ == "__main__":
    dataset_paths = {
        "Dataset_Main": r"d:\Projects\sih-identity-screening-main\Dataset",
        "Data_Morphed": r"d:\Projects\sih-identity-screening-main\data\morphed",
        "Data_Labeled": r"d:\Projects\sih-identity-screening-main\data\aadhar_labeled_imgs"
    }
    create_splits(dataset_paths)
