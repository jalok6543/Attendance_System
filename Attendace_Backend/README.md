# Attendance Backend API

FastAPI backend for enterprise attendance tracking with facial recognition (InsightFace RetinaFace + ArcFace).

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | Supabase (PostgreSQL) |
| ML | InsightFace (buffalo_l), OpenCV, MediaPipe |
| Auth | JWT (python-jose), bcrypt |
| SMS | Fast2SMS (optional) |

## Prerequisites

- Python 3.11 or 3.12
- Supabase account
- (Optional) Twilio for SMS alerts

## Quick Start

### 1. Clone and setup

```bash
git clone https://github.com/jalok6543/Attendace_Backend.git
cd Attendace_Backend

python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 2. Environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

**Required variables:**

| Variable | Description | Where to get |
|----------|-------------|--------------|
| `SUPABASE_URL` | Project URL | Supabase → Settings → API |
| `SUPABASE_KEY` | Anon/public key | Supabase → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (keep secret!) | Supabase → Settings → API |
| `SECRET_KEY` | JWT signing key | Generate: `openssl rand -hex 32` |

**Optional (Fast2SMS):** `FAST2SMS_API_KEY` — get from [fast2sms.com](https://www.fast2sms.com)

### 3. Run database migration

In Supabase **SQL Editor**, run the full contents of `database/001_initial_schema.sql`.

### 4. Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/api/docs  
- Health: http://localhost:8000/health  
- DB check: http://localhost:8000/health/db  

**Note:** First run downloads InsightFace `buffalo_l` model (~300MB) to `~/.insightface/models`.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | JWT signing secret |
| `SUPABASE_URL` | Yes | — | Supabase project URL |
| `SUPABASE_KEY` | Yes | — | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 1440 | Token expiry |
| `FAST2SMS_API_KEY` | No | — | Fast2SMS API key for SMS alerts |
| `FACE_RECOGNITION_THRESHOLD` | No | 0.68 | Face match threshold |
| `MAX_FACES_DETECT` | No | 3 | Max faces per frame |
| `CORS_ORIGINS` | No | localhost:5173,3000 | Allowed CORS origins |

---

## Default Credentials (after migration)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@school.com | Password123! |
| Teacher | teacher@school.com | Password123! |

---

## API Endpoints

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/auth/me` | Current user |
| GET | `/api/v1/auth/reset-admin-password` | Reset admin password (dev) |

### Attendance

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/attendance/check-in` | Mark check-in |
| POST | `/api/v1/attendance/check-out` | Mark check-out |
| GET | `/api/v1/attendance/dashboard-stats` | Dashboard stats |
| GET | `/api/v1/attendance/analytics-chart` | Chart data |
| GET | `/api/v1/attendance/attendance-report` | Export report |
| GET | `/api/v1/attendance/student/{id}` | Student attendance |
| GET | `/api/v1/attendance/summary/{sid}/{subid}` | Summary |
| GET | `/api/v1/attendance/daily-report` | Daily report |
| POST | `/api/v1/attendance/manual-override` | Manual override |

### Face

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/face/register/{student_id}` | Register face |
| POST | `/api/v1/face/verify` | Verify single face |
| POST | `/api/v1/face/verify-multi` | Verify multiple faces |
| POST | `/api/v1/face/verify-multi-stable` | 3-frame stable verify |
| POST | `/api/v1/face/verify-liveness` | Liveness check |

### Students

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/students` | List students |
| POST | `/api/v1/students` | Create student |
| POST | `/api/v1/students/register-with-face` | Create + register face |
| GET | `/api/v1/students/{id}` | Get student |
| PATCH | `/api/v1/students/{id}` | Update student |
| DELETE | `/api/v1/students/{id}` | Delete student (admin only) |

### Subjects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/subjects` | List subjects |
| POST | `/api/v1/subjects` | Create subject |
| GET | `/api/v1/subjects/{id}` | Get subject |

### Teachers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/teachers` | List teachers |
| POST | `/api/v1/teachers/ensure` | Ensure teacher record |

### Change Requests

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/student-change-requests` | List (admin: all; teacher: own) |
| GET | `/api/v1/student-change-requests/pending-count` | Pending count |
| GET | `/api/v1/student-change-requests/{id}` | Get request |
| POST | `/api/v1/student-change-requests` | Create (teacher only) |
| POST | `/api/v1/student-change-requests/{id}/approve` | Approve (admin) |
| POST | `/api/v1/student-change-requests/{id}/reject` | Reject (admin) |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/health/db` | Database connectivity |

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `users` | Admin/teacher accounts |
| `teachers` | Teacher records (1:1 with users) |
| `students` | Students (name, email, roll_number, parent_phone, class) |
| `subjects` | Subjects (name, teacher_id) |
| `attendance` | Per student/subject/date (check_in, check_out, status) |
| `face_embeddings` | 512-D face vectors per student |
| `logs` | Audit trail |
| `student_change_requests` | Teacher change requests (pending/approved/rejected) |

Run `database/001_initial_schema.sql` in Supabase to create all tables.

---

## Project Structure

```
Attendace_Backend/
├── app/
│   ├── controllers/     # API routes
│   ├── services/        # Business logic
│   ├── repositories/    # Database access
│   ├── models/          # Pydantic schemas
│   └── core/            # Config, exceptions, security, scheduler
├── ml/                  # InsightFace recognition
├── database/            # SQL migrations
├── scripts/             # Seed, reset passwords
├── requirements.txt
├── .env.example
└── README.md
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate venv, run `pip install -r requirements.txt` |
| Supabase connection failed | Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` |
| InsightFace download slow | First run downloads ~300MB; wait for completion |
| Port 8000 in use | Use `--port 8001` with uvicorn |

---

## License

MIT
