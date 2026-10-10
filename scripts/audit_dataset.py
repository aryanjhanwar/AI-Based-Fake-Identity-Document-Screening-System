import os
import glob
import json
import hashlib
from collections import defaultdict
from PIL import Image

def get_image_hash(filepath):
    """Compute MD5 hash to find exact duplicates."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest()
    except Exception:
        return None

def audit_dataset(dataset_roots, output_json="dataset_audit_report.json"):
    print("Starting dataset audit...")
    
    report = {
        "total_images": 0,
        "class_counts": {"Genuine": 0, "Forged": 0, "Unknown": 0},
        "category_counts": defaultdict(int),
        "source_counts": defaultdict(int),
        "formats": defaultdict(int),
        "color_modes": defaultdict(int),
        "corrupt_images": 0,
        "corrupt_files_list": [],
        "exact_duplicates": 0,
        "resolutions": defaultdict(int)
    }
    
    image_hashes = {}
    
    for source_name, root_dir in dataset_roots.items():
        if not os.path.exists(root_dir):
            print(f"Warning: Root directory {root_dir} does not exist.")
            continue
            
        for ext in ('**/*.jpg', '**/*.jpeg', '**/*.png'):
            for filepath in glob.iglob(os.path.join(root_dir, ext), recursive=True):
                report["total_images"] += 1
                report["source_counts"][source_name] += 1
                
                # Infer category and class from path based on known structure
                path_parts = filepath.split(os.sep)
                
                # Determine Genuine/Forged
                img_class = "Unknown"
                if "Original" in path_parts or "aadhar_labeled_imgs" in path_parts:
                    img_class = "Genuine"
                elif "Fake" in path_parts or "morphed" in path_parts:
                    img_class = "Forged"
                    
                report["class_counts"][img_class] += 1
                
                # Determine Category
                category = "Unknown"
                path_lower = filepath.lower()
                if "aadhar" in path_lower:
                    category = "Aadhaar"
                elif "PAN" in path_parts:
                    category = "PAN"
                elif "Passport" in path_parts:
                    category = "Passport"
                    
                report["category_counts"][category] += 1
                
                # Check for corruption and get image details
                try:
                    with Image.open(filepath) as img:
                        img.verify() # verify integrity
                    with Image.open(filepath) as img:
                        report["formats"][img.format] += 1
                        report["color_modes"][img.mode] += 1
                        res = f"{img.width}x{img.height}"
                        report["resolutions"][res] += 1
                except Exception as e:
                    report["corrupt_images"] += 1
                    report["corrupt_files_list"].append(filepath)
                    continue
                    
                # Check for exact duplicates
                file_hash = get_image_hash(filepath)
                if file_hash:
                    if file_hash in image_hashes:
                        report["exact_duplicates"] += 1
                    else:
                        image_hashes[file_hash] = filepath

    # Convert defaultdicts to dicts for JSON serialization
    report["category_counts"] = dict(report["category_counts"])
    report["source_counts"] = dict(report["source_counts"])
    report["formats"] = dict(report["formats"])
    report["color_modes"] = dict(report["color_modes"])
    
    # Keep only top 10 resolutions in report to avoid massive JSON
    sorted_res = sorted(report["resolutions"].items(), key=lambda x: x[1], reverse=True)
    report["top_10_resolutions"] = dict(sorted_res[:10])
    del report["resolutions"]

    with open(output_json, 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"Audit complete! Generated report at {output_json}")
    print(f"Total Images: {report['total_images']}")
    print(f"Genuine: {report['class_counts']['Genuine']}, Forged: {report['class_counts']['Forged']}")
    print(f"Corrupt Images: {report['corrupt_images']}, Duplicates: {report['exact_duplicates']}")

if __name__ == "__main__":
    dataset_paths = {
        "Dataset_Main": r"d:\Projects\sih-identity-screening-main\Dataset",
        "Data_Morphed": r"d:\Projects\sih-identity-screening-main\data\morphed",
        "Data_Labeled": r"d:\Projects\sih-identity-screening-main\data\aadhar_labeled_imgs"
    }
    audit_dataset(dataset_paths)
