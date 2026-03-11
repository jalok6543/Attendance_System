# Attendance Frontend

React frontend for the Attendance Tracking System with face recognition. Connects to the [Attendace_Backend](https://github.com/ManasOP1/Attendace_Backend) API.

**Live Backend:** https://attendace-backend-wtwf.onrender.com/api/v1

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | React 19, Vite 7 |
| Language | TypeScript |
| Styling | TailwindCSS 4 |
| Data | TanStack Query (React Query) |
| Charts | Recharts |
| HTTP | Axios |
| Icons | Lucide React |
| Realtime | Supabase client |

## Prerequisites

- Node.js 20+
- Backend API running (see [Attendace_Backend](https://github.com/ManasOP1/Attendace_Backend))
- Supabase project (for Realtime)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/ManasOP1/Attendance_Frontend.git
cd Attendance_Frontend

npm install
```

### 2. Environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API URL. Dev: `http://localhost:8000/api/v1` • Prod: `https://attendace-backend-wtwf.onrender.com/api/v1` |
| `VITE_SUPABASE_URL` | No | Supabase URL (for Realtime) |
| `VITE_SUPABASE_ANON_KEY` | No | Supabase anon key (for Realtime) |

### 3. Run

```bash
npm run dev
```

App: http://localhost:5173

### 4. Build for production

```bash
npm run build
```

---

## Features

| Feature | Description |
|--------|-------------|
| **Login** | JWT auth, role-based (Admin/Teacher) |
| **Dashboard** | Stats cards, attendance chart, date/subject filter, Excel export |
| **Attendance** | Face capture page with check-in/check-out, session log |
| **Students** | List, add, edit, delete (admin), face registration |
| **Subjects** | Create subjects, assign teachers |
| **Requests** | Teachers submit change requests; admin approves/rejects |
| **Realtime** | Live updates via Supabase |

---

## Project Structure

```
Attendance_Frontend/
├── public/
├── src/
│   ├── components/     # Layout, modals, shared UI
│   ├── context/       # AuthContext, ToastContext
│   ├── hooks/         # useAuth, useRealtime
│   ├── pages/         # Login, Dashboard, Students, Attendance, Requests
│   ├── services/      # api.ts
│   └── App.tsx
├── index.html
├── package.json
├── .env.example
└── README.md
```

---

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server |
| `npm run build` | Production build |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

---

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@school.com | Password123! |
| Teacher | teacher@school.com | Password123! |

---

## Deploy on Vercel

1. Push this repo to GitHub and connect it to Vercel.
2. Add **Environment Variable** in Vercel:
   - **Name:** `VITE_API_URL`
   - **Value:** `https://attendace-backend-wtwf.onrender.com/api/v1`
3. Build command: `npm run build` • Output directory: `dist`

---

## License

MIT
