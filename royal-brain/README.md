# Royal BrAIn™ - Genealogy & Succession Verification System

**Version**: 1.0.0  
**Status**: ✅ feature-complete • deployable with correct env + ops setup

---

## ✅ PRODUCTION READINESS CHECKLIST

- [x] Backend APIs - All 9 engines (Days 1-9)
- [x] Frontend UI - Full CRUD (Admin, Sources, Persons, Relationships)
- [x] Dockerfiles - Backend + Frontend production builds
- [x] Docker Compose - Full stack with health checks
- [x] Database - PostgreSQL with migrations
- [x] Environment Config - .env.example files
- [x] Demo Data - 4 royal houses seeding script
- [x] Documentation - Whitepaper, audit, deployment guides
- [x] Security - JWT, RBAC, audit logging, password hashing

---

## 🚀 QUICK START (Docker - Recommended)

```bash
# 1) Create env file
cp .env.example .env.production
# Edit: set at least JWT_SECRET (and optionally BOOTSTRAP_ADMIN_*).

# 2) Start services (production compose)
RB_ENV=production docker compose -f docker-compose.prod.yml up -d --build

# 3) Access system
Frontend: http://localhost:3000
Backend:  http://localhost:8000
API Docs: http://localhost:8000/docs
```

**Login:** configure BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD to create an initial ADMIN.

---

## 🐳 DOCKER DEPLOYMENT

### **Start Full Stack**
```bash
docker-compose up -d
```

Services running:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000  
- **PostgreSQL**: localhost:5432

### **View Logs**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### **Seed Demo Data**
```bash
docker-compose exec backend python seed_demo_data.py
```

### **Stop Services**
```bash
docker-compose down
```

---

## 💻 LOCAL DEVELOPMENT

### **Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Create repo-root env file (preferred): copy ../.env.example -> ../.env.dev
# and set RB_ENV=dev (or set env vars directly).
alembic upgrade head
python seed_demo_data.py
uvicorn app.main:app --reload
```

### **Frontend**
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## ☁️ CLOUD DEPLOYMENT

### **AWS EC2 + RDS**
```bash
# On EC2 instance
git clone <repo>
cd royal-brain
cp .env.example .env.production
# Configure DATABASE_URL with RDS endpoint
RB_ENV=production docker compose -f docker-compose.prod.yml up -d
```

### **DigitalOcean App Platform**
1. Connect GitHub repo
2. Add Backend (Dockerfile: `/backend/Dockerfile`)
3. Add Frontend (Dockerfile: `/frontend/Dockerfile`)
4. Add PostgreSQL database
5. Set environment variables
6. Deploy

### **Railway**
```bash
railway login
cd backend && railway up
cd ../frontend && railway up
```

---

## 🧪 USER JOURNEY TESTING

### **1. Admin Creates User**
```
/dashboard/admin/users → "+ Add User" → researcher@test.com → RESEARCHER
✅ User appears, can login
```

### **2. Data Entry**
```
/dashboard/data/sources → Create source
/dashboard/data/persons → Create person (requires source)
/dashboard/data/relationships → Link persons
✅ All validated, no duplicates/invalid data
```

### **3. Succession Evaluation**
```
/dashboard/succession → Elizabeth II → Prince George → Cognatic → Evaluate
✅ VALID path shown
"Explain" → ✅ Explanation generated (uses OpenAI if configured; otherwise deterministic fallback)
```

---

## 📊 DEMO DATA

**16 persons, 12 relationships, 4 royal houses:**
- House of Windsor (British) - 5 persons
- House of Bourbon (Spanish) - 4 persons  
- House of Savoy (Italian) - 4 persons
- House of Saud (Saudi) - 3 persons

---

## 🔐 SECURITY SETUP

**Required Environment Variables (backend):**
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/royal_brain
JWT_SECRET=<random-32+ char string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=https://your-frontend-domain

# Optional first-run authority bootstrap
BOOTSTRAP_ADMIN_EMAIL=admin@your-domain
BOOTSTRAP_ADMIN_PASSWORD=<secure-password>

# Optional AI + anchoring
OPENAI_API_KEY=<optional>
EVM_RPC_URL=<optional>
EVM_CHAIN_ID=<optional>
EVM_PRIVATE_KEY=<optional>
```

**Frontend variables (server/runtime):**
```bash
BACKEND_URL=https://your-backend-domain
# Optional (only needed if calling the backend directly from the browser)
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain
```

**Production Checklist:**
- [ ] Set strong JWT_SECRET (use: `openssl rand -hex 32`)
- [ ] Set strong BOOTSTRAP_ADMIN_PASSWORD (or disable bootstrap entirely)
- [ ] Enable HTTPS/SSL
- [ ] Update CORS_ORIGINS
- [ ] Never commit .env
- [ ] Regular backups

---

## 📚 DOCUMENTATION

- Technical Whitepaper: `/backend/TECHNICAL_WHITEPAPER.md`
- System Audit: `/backend/SYSTEM_AUDIT_AND_OPERATOR_GUIDANCE.md`
- Deployment Guide: `/DEPLOYMENT.md`
- API Docs: http://localhost:8000/docs

---

## 🏗️ SYSTEM ARCHITECTURE

```
Frontend (Next.js) ←→ Backend (FastAPI) ←→ Database (PostgreSQL)
     │                      │                      │
  Admin UI          9 Engines (Genealogy,    Persons, Sources
  Data Entry        Succession, AI, etc.)    Relationships
  Succession UI     JWT Auth, RBAC           Audit Logs
```

**Everything is connected end-to-end. No standalone code.**

---

## 🆘 TROUBLESHOOTING

**Frontend can't connect:**
```bash
# Check backend URL
curl http://localhost:8000/ready
```

**Database errors:**
```bash
docker-compose exec backend alembic upgrade head
```

**Docker rebuild:**
```bash
docker-compose down -v
docker system prune -a
docker-compose up -d --build
```

---

## ✅ DEPLOYMENT VERIFICATION

After deployment, verify:
- [ ] Frontend loads
- [ ] Admin can login
- [ ] API docs accessible
- [ ] Create user works
- [ ] Data entry persists
- [ ] Succession evaluation runs
- [ ] Explanation generates (uses OpenAI if configured; otherwise deterministic fallback)

---

## 🏆 PRODUCTION STATUS

**✅ READY TO DEPLOY**

All features implemented and wired:
- Backend APIs complete (all 9 engines)
- Frontend UI complete (CRUD interfaces)
- Docker containerization ready
- Database migrations automated
- Security configured
- Documentation complete

**Deploy with confidence.**

---

**Tech Stack**: Python 3.11 • FastAPI • PostgreSQL • Next.js 16 • TypeScript • Docker
