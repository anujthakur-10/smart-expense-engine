# 🧾 Smart Expense Engine & Predictive Analytics for Indian SMEs

> AI-powered invoice processing for Indian micro-SMEs (Kirana stores, retailers). Hindi + English OCR, GST intelligence, multi-model expense forecasting.

![License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![React](https://img.shields.io/badge/React-18-61DAFB)

## ✨ Features

- **🔤 Multimodal OCR** — PaddleOCR reads Hindi + English handwriting and printed text
- **📸 Dirty Image Cleanup** — OpenCV pipeline: shadow removal, binarization, deskew
- **📄 Multi-page PDF** — PyMuPDF converts PDFs to images, processes each page
- **🧾 Indian GST Engine** — Auto CGST/SGST/IGST split, GSTIN validation, 37 state codes
- **🔮 3-Model Forecasting** — Prophet + XGBoost (best) + LightGBM with comparison
- **🚨 Fraud Detection** — Hash + exact + fuzzy matching for duplicate invoices
- **🔐 Authentication** — Supabase Auth (email/password + JWT)
- **☁️ Cloud Storage** — Supabase Storage for invoice files
- **📊 Analytics Dashboard** — Recharts with expense trends, GST breakdown, vendor pie

## 🏗️ Architecture

```
Frontend (React/Vite) → Backend (FastAPI) → Supabase (PostgreSQL + Auth + Storage)
     Vercel                Railway/Render           Cloud Database
```

### Dual-Track ML Pipeline

| Track | Purpose | Technology |
|-------|---------|-----------|
| **Track A** (Production) | Real-time inference | PaddleOCR (Hindi+English) |
| **Track B** (Academic) | Model fine-tuning demo | Donut on CORD dataset (Colab) |

## 🚀 Quick Start

### 1. Supabase Setup

1. Create project at [supabase.com](https://supabase.com)
2. Enable Email Auth: Authentication → Providers → Email
3. Create Storage bucket: Storage → New bucket → `invoices` (public)
4. Copy credentials from: Settings → API

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Create .env from template
cp ../.env.example .env
# Fill in your Supabase credentials

# Seed sample data (18 months)
python seed_data.py

# Start server
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install

# Create .env
cp .env.example .env.local
# Fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY

npm run dev
```

Open http://localhost:5173 → Register → Start uploading invoices!

### 4. Colab Training (Track B)

1. Open [Google Colab](https://colab.research.google.com)
2. Upload `colab/train_model.py`
3. Set Runtime → GPU (T4)
4. Run all cells (~30-45 min training)

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload/` | Upload invoice → OCR → Parse → GST → Save |
| GET | `/api/invoices/` | List all invoices (paginated) |
| PUT | `/api/invoices/{id}` | Update/edit invoice |
| DELETE | `/api/invoices/{id}` | Delete invoice |
| GET | `/api/dashboard/summary` | Dashboard stats |
| GET | `/api/dashboard/gst-summary` | Monthly GST breakdown |
| GET | `/api/dashboard/monthly-trend` | Expense trend |
| GET | `/api/forecast/expenses` | Expense forecast |
| GET | `/api/forecast/gst` | GST liability forecast |
| GET | `/api/forecast/compare` | Compare all 3 models |

## 🚢 Deployment

### Backend → Railway/Render

```bash
# Push to GitHub, then connect repo in Railway/Render dashboard
# Set environment variables from .env.example
# Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend → Vercel

```bash
# Connect GitHub repo in Vercel dashboard
# Framework: Vite
# Build command: npm run build
# Output: dist
# Environment variables: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_URL
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Recharts, Supabase Auth |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | Supabase PostgreSQL |
| OCR | PaddleOCR (Hindi + English) |
| Image Processing | OpenCV, PyMuPDF |
| Forecasting | Prophet, XGBoost, LightGBM, scikit-learn |
| Auth | Supabase Authentication (JWT) |
| Storage | Supabase Storage |
| Deployment | Vercel (FE) + Railway/Render (BE) |

## 📁 Project Structure

```
├── backend/           # FastAPI Python Backend
│   ├── services/      # ML pipeline + business logic
│   ├── routers/       # API endpoints
│   ├── models/        # SQLAlchemy ORM
│   └── schemas/       # Pydantic schemas
├── frontend/          # React.js Dashboard
│   └── src/
│       ├── components/  # Reusable UI
│       ├── pages/       # Route pages
│       └── services/    # API layer
├── colab/             # Track B training script
└── sample_invoices/   # Test images
```

## 👨‍💻 Author

4th Year B.Tech Major Project — Smart Expense Engine & Predictive Analytics for Indian SMEs

---

*Built with ❤️ for Indian SMEs — Jai Hind! 🇮🇳*
