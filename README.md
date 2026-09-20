# PermiTrack — Split Frontend & Backend Architecture

PermiTrack is separated into two standalone, independently deployable projects:

```
leave_flask_app/
├── backend/            # Flask REST API + PostgreSQL/MySQL Database & Models
└── frontend/           # Vite + React + TypeScript + Tailwind CSS Single Page App
```

---

## 🚀 Deployment Guide

### 1. Backend Deployment (`backend/`)
**Target Platforms**: Render, Railway, Fly.io, Heroku, AWS ECS / EC2, VPS.

#### Environment Variables (Production)
Set the following environment variables in your backend hosting platform:

```env
APP_ENV=production
SECRET_KEY=<your-production-secret-key>
DATABASE_URL=postgresql://postgres:<password>@<supabase-or-db-host>:5432/postgres?sslmode=require
CORS_ALLOWED_ORIGINS=https://your-frontend-app.vercel.app
STORAGE_BACKEND=s3 # or oci / supabase / local
STORAGE_BUCKET=<your-cloud-bucket>
```

#### Start Command
```bash
cd backend
pip install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:5000 "leave_app:create_app()"
```

---

### 2. Frontend Deployment (`frontend/`)
**Target Platforms**: Vercel, Netlify, Cloudflare Pages, AWS Amplify.

#### Environment Variables (Production)
Set the following environment variable in your frontend build settings:

```env
VITE_API_BASE_URL=https://your-backend-api.onrender.com/api/v1
```

#### Build Command & Output Directory
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

---

## 💻 Local Development Setup

### Running Backend Locally
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
python app.py
# Backend server runs on http://127.0.0.1:5000
```

### Running Frontend Locally
```bash
cd frontend
npm install
npm run dev
# Frontend dev server runs on http://localhost:5173
```

---

## 🧪 Testing

### Run Backend Tests (24/24 tests)
```bash
cd backend
python -m pytest
```

### Run Frontend Type Check & Build
```bash
cd frontend
npm run build
```
