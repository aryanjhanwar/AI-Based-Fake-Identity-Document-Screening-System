# IDShield Pro — Frontend Application

Modern Single Page Application (SPA) built with **React 19 + TypeScript + Vite + Tailwind CSS** for the AI-Based Identity Document Screening System.

---

## 📁 Directory Layout

```
frontend/
├── public/
│   └── _redirects        # Netlify SPA redirect rules
├── src/
│   ├── components/       # Layout and UI primitives (Radix + Tailwind)
│   ├── pages/            # Dashboard, Upload, Results, Reviews, Analytics, Settings
│   ├── lib/
│   │   ├── api.ts        # Axios client instance (resolves VITE_API_URL)
│   │   └── utils.ts      # Tailwind class merging utility
│   ├── App.tsx           # Application routes
│   ├── main.tsx          # React DOM entrypoint
│   └── index.css         # Theme tokens & styling
├── netlify.toml          # Netlify build configuration
├── package.json          # Dependencies & scripts
└── vite.config.ts        # Vite build & local API proxy configuration
```

---

## 🚀 Independent Local Development

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
# Running on http://127.0.0.1:3000
```

By default, Vite proxies `/api/*` requests to `http://127.0.0.1:5000` (the Flask backend).

---

## ☁️ Independent Deployment

### Option 1: Deploy to Netlify
1. In Netlify, click **"Add new site"** $\rightarrow$ **"Import an existing project"**.
2. Select your repository.
3. Configure build settings:
   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `dist`
4. Set Environment Variable:
   - `VITE_API_URL`: Your deployed backend URL (e.g. `https://idshield-backend.onrender.com`).
5. Click **Deploy Site**.

### Option 2: Deploy to Vercel
1. Import repository in Vercel.
2. Set **Root Directory** to `frontend`.
3. Set Environment Variable `VITE_API_URL` to your backend URL.
4. Framework preset will automatically detect **Vite**. Click **Deploy**.
