# IDShield Pro — AI-Powered Identity Document Screening System

An advanced, end-to-end identity screening and anti-fraud platform. Built with a modern **React + TypeScript + Vite** frontend and a high-performance **Python Flask + PyTorch + PaddleOCR** backend.

Designed for instant detection of forged Indian identity documents (**Aadhaar, PAN, Passport, Voter ID, Driving License**), extraction of cardholder details (Name, Age, DOB, Gender, ID Number), and evaluation of exact **Real vs Fake Probabilities** with a strict 3-tier verdict (**Pass**, **Suspicious**, **Failed**).

---

## 🏗 Architecture & Repository Layout

```
sih-identity-screening-main/
│
├── frontend/                       # 🌐 React + TypeScript Frontend (Deploy independently to Netlify/Vercel)
│   ├── public/
│   │   └── _redirects              # Netlify client-side SPA routing rules
│   ├── src/
│   │   ├── components/ui/          # Radix & Tailwind UI component library
│   │   ├── pages/                  # Dashboard, Analyze, Results, Records, Review
│   │   ├── lib/api.ts              # Axios client (reads VITE_API_URL for Render backend)
│   │   ├── App.tsx                 # Routing & Layout
│   │   └── main.tsx
│   ├── netlify.toml                # Netlify build configuration
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
│
├── backend/                        # 🧠 Python Flask & Forensic Backend (Deploy independently to Render/Docker)
│   ├── modules/                    # Forensic & OCR Modules (classifier, OCR, ELA, metadata, stamps, etc.)
│   ├── artifacts/                  # Offline Pretrained Model Weights (fast_classifier.pkl, id_classifier.pth)
│   ├── Dataset/                    # Indian ID Samples (Aadhaar, PAN, Passport)
│   ├── scripts/                    # Utility Scripts, Model Training & Benchmarks
│   ├── uploads/                    # Temporary document processing cache
│   ├── server.py                   # Production Flask REST API & WSGI Entrypoint
│   ├── config.py                   # Central configurations, thresholds, and weights
│   ├── requirements.txt            # Production Python dependencies
│   ├── Dockerfile                  # Containerized deployment spec
│   ├── Procfile                    # Render / Heroku WSGI process configuration
│   ├── render.yaml                 # Render Blueprint specification
│   ├── test_api.py                 # Automated API test suite
│   └── README.md
│
├── render.yaml                     # ☁️ Root Render Blueprint (configures rootDir: backend)
├── netlify.toml                    # 🌐 Root Netlify build configuration (base: frontend)
├── SYSTEM_ARCHITECTURE.md          # 📋 Complete System Architecture & Audit Specification
└── README.md
```

---

## 🚀 Deployment Guide

### Option 1: Deploy Frontend to Netlify

The frontend is a static Single Page Application (SPA) built with Vite and React.

#### Steps:
1. **Push your repository to GitHub / GitLab**.
2. Go to [Netlify](https://app.netlify.com/) and click **"Add new site"** $\rightarrow$ **"Import an existing project"**.
3. Select your repository.
4. Netlify will automatically detect the settings from [`netlify.toml`](file:///d:/Projects/sih-identity-screening-main/netlify.toml):
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
5. **Set Environment Variable** (under *Site configuration* $\rightarrow$ *Environment variables*):
   - `VITE_API_URL`: Your deployed Render backend URL (e.g. `https://idshield-backend.onrender.com`).
6. Click **Deploy Site**.
   - Netlify will build the frontend and serve it globally on a custom `.netlify.app` domain.
   - SPA route reloads (`/upload`, `/results`, `/results/:id`) work automatically via [`public/_redirects`](file:///d:/Projects/sih-identity-screening-main/frontend/public/_redirects).

---

### Option 2: Deploy Backend to Render

The backend is a Flask REST API running with Gunicorn.

#### Method A: Using 1-Click Render Blueprint (`render.yaml`)
1. In Render, select **"Blueprints"** $\rightarrow$ **"New Blueprint Instance"**.
2. Connect your repository.
3. Render will parse [`render.yaml`](file:///d:/Projects/sih-identity-screening-main/render.yaml) and configure the web service automatically:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180`
   - **Health Check Path**: `/api/system/health`
4. Click **Apply**.

#### Method B: Manual Web Service on Render
1. Click **"New +"** $\rightarrow$ **"Web Service"**.
2. Connect your repository.
3. Configure the service:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180`
4. **Environment Variables**:
   - `PYTHON_VERSION`: `3.11.9`
   - `FLAGS_enable_pir_api`: `0`
5. Click **Create Web Service**.

> **Note on Render Free Tier**: PaddleOCR models take ~300MB RAM. The service is pre-configured with 1 Gunicorn worker and 4 threads (`--workers 1 --threads 4`) to prevent memory exhaustion and `--timeout 180` to allow sufficient time for CPU-based OCR inference.

---

## 💻 Local Development

### 1. Start the Flask Backend
```bash
# Activate virtual environment
venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py
# Running on http://127.0.0.1:5000
```

### 2. Start the React Frontend
```bash
cd frontend
npm install
npm run dev
# Running on http://127.0.0.1:3000
```

Vite proxies all `/api/*` calls directly to the local Flask backend on port `5000`.

### 3. Verify System Health & Run Automated Tests
```bash
python test_api.py
```

---

## 🎯 Key Features

- **OCR Cardholder Extraction**: Automatically detects Name, Age, Date of Birth, Gender, ID Number, and Document Type.
- **Real vs. Fake Probability (%)**: Calculates exact probability score for genuine vs. fraudulent IDs.
- **3-Tier Classification**: Clear categorization into **Pass**, **Suspicious**, or **Failed**.
- **Collapsible Technical Forensics**: Overly technical OpenCV / ML diagnostics (Laplacian blur variance, HOG vectors, HSV gamut, ELA compression matrices) are collapsed by default into an optional audit accordion.