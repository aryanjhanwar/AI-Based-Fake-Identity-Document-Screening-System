import axios from 'axios';

// When deployed on Netlify, specify VITE_API_URL in Netlify Environment Variables:
// e.g. VITE_API_URL = "https://verishieldai-backend.onrender.com"
// In local development or self-hosted mode, defaults to '/api' (proxied by Vite)
const rawUrl = (import.meta.env.VITE_API_URL || '').trim();
const cleanUrl = rawUrl.replace(/\/+$/, '');

export const API_BASE = cleanUrl
  ? (cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`)
  : '/api';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 180000, // 180s — allows sufficient time for OCR and ML inference on CPU
});

// Expose raw API URL for direct asset links (uploaded images, sample files)
export const API_URL = API_BASE;
