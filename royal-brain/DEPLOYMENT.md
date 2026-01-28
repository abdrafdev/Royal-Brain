# Royal BrAIn™ Deployment Guide

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- SQLite (included with Python)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create repo-root env file (preferred)
# From /royal-brain/backend:
copy ..\.env.example ..\.env.dev
# (Mac/Linux):
# cp ../.env.example ../.env.dev
#
# Edit ../.env.dev and set at least:
# - DATABASE_URL=sqlite:///./rb_dev.db (dev) OR postgresql+psycopg://...
# - JWT_SECRET=<random 32+ chars>
# Optional:
# - BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD (initial ADMIN)
# - OPENAI_API_KEY (AI explanations; otherwise deterministic fallback)

# Run migrations
alembic upgrade head

# Seed demo data (optional)
python seed_demo_data.py

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will run at: **http://localhost:8000**

Health endpoints:
- Liveness: http://localhost:8000/health
- Readiness (includes DB): http://localhost:8000/ready

API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
# Server-side (used by Next.js route handlers + server components)
echo "BACKEND_URL=http://localhost:8000" > .env.local

# Optional: build-time/public variable (only needed if calling the backend directly from the browser)
echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000" >> .env.local

# Start frontend
npm run dev
```

Frontend will run at: **http://localhost:3000**

### Initial Admin (Bootstrap)
Royal BrAIn does not ship with a hardcoded admin account.

To create the first **ADMIN** automatically on backend startup, set:
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`

---

## 📊 Demo Data

The seed script creates:
- **10 sources** (birth certificates, royal decrees, historical records)
- **16 persons** across 4 royal houses
- **12 relationships** (parent-child, marriages)
- **4 families** (Windsor, Bourbon, Savoy, Saud)

### Royal Houses Included:
1. **House of Windsor** (British) - 5 persons, 4 generations
2. **House of Bourbon** (Spanish) - 4 persons, 3 generations
3. **House of Savoy** (Italian) - 4 persons, 4 generations
4. **House of Saud** (Saudi) - 3 persons, 3 generations

---

## 🐳 Docker Deployment

### Docker Compose (Recommended)

```bash
# Development stack (bind mounts, auto-seeds demo data)
docker compose -f docker-compose.yml up --build

# Production-style stack (no bind mounts, runs migrations)
# Requires JWT_SECRET (and optionally BOOTSTRAP_ADMIN_*)
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop services
docker compose -f docker-compose.prod.yml down
```

Services:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432

### Environment Variables for Docker

Create an env file in the repo root (for example, `.env.production` used with `docker compose --env-file`):

```env
# Database (SQLAlchemy URL)
DATABASE_URL=postgresql+psycopg://royal:brain@db:5432/royalbrain

# Backend (required)
JWT_SECRET=your_production_jwt_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:3000

# Optional first-run admin bootstrap (creates ADMIN if email doesn't exist)
BOOTSTRAP_ADMIN_EMAIL=admin@royalbrain.ai
BOOTSTRAP_ADMIN_PASSWORD=your_secure_password

# Optional AI + anchoring
OPENAI_API_KEY=
EVM_RPC_URL=
EVM_CHAIN_ID=
EVM_PRIVATE_KEY=
EVM_EXPLORER_TX_URL_BASE=

# Frontend (server/runtime)
BACKEND_URL=http://backend:8000
# Optional (only needed for direct browser calls)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## ☁️ Cloud Deployment

### AWS (EC2 + RDS)

1. **Launch EC2 instance** (t3.medium or larger)
   - Ubuntu 22.04 LTS
   - Open ports: 80, 443, 8000, 3000

2. **Setup RDS PostgreSQL**
   - PostgreSQL 15+
   - Update DATABASE_URL in .env

3. **Deploy backend**:
```bash
ssh ubuntu@your-ec2-ip
git clone <your-repo>
cd royal-brain/backend
# Follow backend setup steps above
# Use systemd or PM2 to keep service running
```

4. **Deploy frontend**:
```bash
cd ../frontend
npm run build
npm start
# Or use PM2: pm2 start npm --name "royal-brain-frontend" -- start
```

5. **Setup Nginx** (reverse proxy):
```nginx
# IMPORTANT: this project uses Next.js /api/* routes (login + authenticated proxy).
# Do NOT proxy /api/* to FastAPI on the same domain, or you'll break the frontend.

# Frontend (Next.js)
server {
    listen 80;
    server_name demo.royalbrain.ai;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend (FastAPI) — recommended on a separate subdomain
server {
    listen 80;
    server_name api.demo.royalbrain.ai;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

6. **Setup SSL** with Let's Encrypt:
```bash
sudo certbot --nginx -d demo.royalbrain.ai
```

### DigitalOcean (App Platform)

1. Create new app
2. Connect GitHub repo
3. Configure services:
   - **Backend**: Python app, port 8000
   - **Frontend**: Node.js app, port 3000
   - **Database**: PostgreSQL managed database

4. Set environment variables in App Platform UI

### Vercel (Frontend) + Railway (Backend)

**Frontend (Vercel)**:
```bash
cd frontend
vercel --prod
# Set BACKEND_URL to your Railway backend URL (server-side)
# Optional: set NEXT_PUBLIC_BACKEND_URL only if you call the backend directly from the browser
```

**Backend (Railway)**:
1. Create new project
2. Deploy from GitHub
3. Add PostgreSQL plugin
4. Set environment variables

---

## 🧪 Testing User Journeys

### 1. Admin Creates User
```bash
1. Login at /login with admin credentials
2. Navigate to /dashboard/admin/users
3. Click "+ Add User"
4. Enter: researcher@test.com, password123, RESEARCHER
5. Click "Create User"
6. ✅ User appears in table
```

### 2. Researcher Enters Data
```bash
1. Login as researcher@test.com
2. Navigate to /dashboard/data
3. Go to Sources → "+ Add Source"
4. Enter: Type=BIRTH_CERTIFICATE, Citation="Test Birth Certificate"
5. ✅ Source created with ID
6. Go to Persons → "+ Add Person" (requires a source)
```

### 3. View Genealogy Tree
```bash
1. Navigate to /dashboard/genealogy
2. Select root person (e.g., "Elizabeth II")
3. Set depth=3, direction=descendants
4. Click "Build Tree"
5. ✅ Tree displays with nodes and relationships
```

### 4. Test Succession Engine
```bash
1. Navigate to /dashboard/succession
2. Select root: "Elizabeth II"
3. Select candidate: "Prince George of Wales"
4. Select rule: "Cognatic"
5. Click "Evaluate"
6. ✅ Result shows VALID with path: Elizabeth II → Charles III → William → George
7. Click "Explain"
8. ✅ Explanation appears (uses OpenAI if configured; otherwise deterministic fallback)
```

### 5. Validate Heraldry
```bash
1. Navigate to /dashboard/heraldry
2. Enter blazon: "Gules, three lions passant guardant Or"
3. Click "Parse & Validate"
4. ✅ Parsed structure shows
5. ✅ Rule-of-tincture validation runs
6. ✅ SVG renders
```

---

## 🔧 Maintenance

### Database Backups
```bash
# SQLite (development)
cp backend/rb_dev.db backend/rb_dev_backup_$(date +%Y%m%d).db

# PostgreSQL (production)
pg_dump -h localhost -U royal royalbrain > backup_$(date +%Y%m%d).sql
```

### Logs
```bash
# Local (non-Docker): logs go to stdout by default

# Docker logs (dev)
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.yml logs -f frontend

# Docker logs (production)
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

### Updating
```bash
# Pull latest code
git pull origin main

# Backend migrations
cd backend
alembic upgrade head

# Frontend rebuild
cd ../frontend
npm install
npm run build
```

---

## 🛡️ Security Checklist

- [ ] Set a strong `JWT_SECRET` (32+ characters)
- [ ] Set a strong `BOOTSTRAP_ADMIN_PASSWORD` (or leave bootstrap unset in production)
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set `CORS_ORIGINS` appropriately (comma-separated)
- [ ] Keep secrets out of git (never commit real `.env.*`)
- [ ] Enable rate limiting (optional: add to FastAPI)
- [ ] Regular database backups
- [ ] Keep dependencies updated

---

## 📞 Support

For issues or questions:
- Technical documentation: `/backend/TECHNICAL_WHITEPAPER.md`
- System audit: `/backend/SYSTEM_AUDIT_AND_OPERATOR_GUIDANCE.md`
- API docs: http://localhost:8000/docs

---

## ✅ System Ready Checklist

- [x] Backend runs without errors
- [x] Frontend loads at http://localhost:3000
- [x] Admin can login
- [x] Demo data seeded (16 persons, 12 relationships)
- [x] User management works (create/edit/delete)
- [x] Source creation works
- [x] Succession engine evaluates correctly
- [x] Explanations generate (uses OpenAI if configured; otherwise deterministic fallback)
- [x] All APIs respond (test at /docs)

**System is production-ready when all checkboxes are complete.**
