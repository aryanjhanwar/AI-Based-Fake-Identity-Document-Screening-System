# IDShield Pro — Backend API Service

High-performance Python Flask + PyTorch + PaddleOCR forensic screening backend for Indian identity documents (**Aadhaar, PAN, Passport, Voter ID, Driving License**).

---

## 📁 Directory Layout

```
backend/
├── modules/                   # Forensic & OCR engines
│   ├── classifier.py          # Fast Random Forest (HOG + HSV) & ELA
│   ├── ocr_extractor.py       # PaddleOCR PP-OCRv6 field extraction
│   ├── metadata_analysis.py   # EXIF tampering & software detection
│   ├── stamp_forensics.py     # Government seal & emblem verification
│   ├── face_verify.py         # Face biometrics & morph detection
│   ├── document_validation.py # Format & MRZ checksum checks
│   ├── risk.py                # Multi-modal risk fusion engine
│   ├── watchlist.py           # Repeat traveller & identity switching check
│   ├── models.py              # Pretrained model loaders
│   ├── inference.py           # Deep learning inference pipeline
│   └── new_forge_detector.py  # Model adapter
│
├── artifacts/                 # Offline pretrained weights
│   ├── fast_classifier.pkl    # Fast Random Forest model (<15ms)
│   ├── id_classifier.pth      # EfficientNet-B0 weights
│   └── forgery_detector/
│       └── efficientnet_b0_best.pth
│
├── Dataset/                   # Indian ID evaluation dataset (Aadhaar, PAN, Passport)
├── scripts/                   # Training, audit, and benchmark scripts
├── uploads/                   # Ephemeral screening upload directory
├── server.py                  # Production Flask REST API entry point
├── config.py                  # Central thresholds, weights, and configurations
├── requirements.txt           # Python production dependencies
├── Dockerfile                 # Containerized deployment spec
├── Procfile                   # WSGI process configuration for Render/Heroku
├── render.yaml                # Render 1-click blueprint spec
├── test_api.py                # Automated API test suite
└── evaluate_dataset.py        # Dataset evaluation benchmark
```

---

## 🚀 Independent Local Development

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the Flask server
python server.py
# Server runs on http://127.0.0.1:5000
```

Verify backend health:
```bash
python test_api.py
# Or open in browser: http://127.0.0.1:5000/api/system/health
```

---

## ☁️ Independent Deployment

### Option 1: Deploy to Render (Web Service)
1. In Render, select **"New +"** $\rightarrow$ **"Web Service"**.
2. Connect your repository.
3. Configure the service:
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180`
   - **Health Check Path:** `/api/system/health`
4. **Environment Variables:**
   - `PYTHON_VERSION`: `3.11.9`
   - `FLAGS_enable_pir_api`: `0`

### Option 2: Deploy using Docker
```bash
# From within the backend/ folder:
docker build -t idshield-backend .
docker run -p 5000:5000 -e PORT=5000 idshield-backend
```

---

## 📡 Key REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/analysis/upload` | Upload & screen ID document |
| `POST` | `/api/screen` | Backward-compatible upload alias |
| `GET` | `/api/analysis` | Filtered list of screenings |
| `GET` | `/api/analysis/<id>` | Full analysis report |
| `GET` | `/api/analysis/<id>/image`| Serve uploaded image |
| `POST` | `/api/analysis/<id>/review`| Analyst sign-off (approve/reject) |
| `GET` | `/api/system/health` | Service health & telemetry |
| `GET` | `/api/system/dashboard/stats` | Dashboard KPI metrics |
| `GET` | `/api/samples` | Pre-configured test sample cards |
