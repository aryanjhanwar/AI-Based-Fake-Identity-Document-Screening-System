"""
Quick API Verification Script
Tests the running Flask backend with both genuine and forged identity documents.
Run: python test_api.py
"""
import os
import requests

API_URL = "http://127.0.0.1:5000"

def test_health():
    print("=== 1. Testing System Health API ===")
    r = requests.get(f"{API_URL}/api/system/health")
    print(f"Status: {r.status_code}")
    print(r.json())
    print()

def test_screen(doc_path: str, label: str):
    print(f"=== Testing Screening: {label} ===")
    if not os.path.exists(doc_path):
        print(f"File not found: {doc_path}")
        return
    with open(doc_path, "rb") as f:
        r = requests.post(f"{API_URL}/api/analysis/upload", files={"file": f})
    print(f"Status Code: {r.status_code}")
    if r.status_code in (200, 201):
        data = r.json()
        person = data.get("person_details", {})
        print(f"ID:                 {data.get('id')}")
        print(f"Classification:     {data.get('classification')}")
        print(f"Verdict:            {data.get('verdict')}")
        print(f"Real Probability:   {data.get('real_probability')}%")
        print(f"Fake Probability:   {data.get('fake_probability')}%")
        print(f"Detected Person:    {person.get('name') or 'Not isolated'}")
        print(f"Detected Age / DOB: {person.get('age') or '—'} / {person.get('dob') or '—'}")
        print(f"Document Type:      {person.get('document_type') or data.get('document_type')}")
        print(f"Summary:            {data.get('human_summary')}")
    else:
        print(f"Error: {r.text}")
    print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    test_health()
    test_screen(os.path.join(BASE_DIR, "Dataset", "Aadhar", "Original", "0005_jpeg_jpg.rf.252590ac8ae7f0f84a08f15a164d6cb0.jpg"), "Genuine Aadhaar")
    test_screen(os.path.join(BASE_DIR, "Dataset", "Aadhar", "Fake", "0_1.jpg"), "Forged Aadhaar")
