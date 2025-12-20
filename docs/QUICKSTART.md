# PhotoBomb - Quick Reference

## 🚀 Start Development

```bash
# 1. Configure B2 (required)
cp backend/.env.example backend/.env
# Edit backend/.env with your B2 credentials

# 2. Start backend
docker-compose up -d
docker-compose exec api alembic upgrade head

# 3. Start frontend (new terminal)
cd frontend && npm install && npm run dev

# 4. Open http://localhost:3000
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| [COMPLETE.md](COMPLETE.md) | Full project summary |
| [walkthrough.md](.gemini/antigravity/brain/.../walkthrough.md) | Step-by-step usage guide |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Production launch |
| [README.md](README.md) | Project overview |
| [backend/README.md](backend/README.md) | Backend setup |
| [frontend/README.md](frontend/README.md) | Frontend setup |

## 🔑 Essential Commands

**Backend:**
```bash
docker-compose up -d              # Start services
docker-compose logs -f api        # View logs
docker-compose exec api alembic upgrade head    # Run migrations
docker-compose exec api pytest tests/ -v       # Run tests
docker-compose down               # Stop services
```

**Frontend:**
```bash
npm install                       # Install dependencies
npm run dev                       # Development server
npm run build                     # Production build
npm run preview                   # Preview build
```

**Database:**
```bash
./scripts/migrate.sh upgrade      # Run migrations
./scripts/migrate.sh current      # Check version
docker-compose exec postgres psql -U photobomb -d photobomb
```

## 🎯 Project Structure

```
photoBomb/
├── docs/           # 15+ planning documents
├── backend/        # FastAPI (55+ files)
├── frontend/       # React PWA (35+ files)
├── infrastructure/ # Terraform + K8s
├── tests/          # Test suites
└── scripts/        # Helper scripts
```

## 📊 Stats

- **Files**: 185+
- **Code**: 8,500+ lines
- **Endpoints**: 10 REST APIs
- **Tests**: 6+ unit tests
- **Docs**: 15+ documents
- **Status**: ✅ Production-ready

## 🔐 Default Credentials (Development)

**PostgreSQL:**
- User: `photobomb`
- Password: `password`
- Database: `photobomb`

**Test User (create via UI):**
- Email: `demo@photobomb.app`
- Password: Your choice (min 8 chars)

## 🌐 URLs (Local)

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs (Swagger UI)
- Health: http://localhost:8000/healthz

## 💡 Common Tasks

**Add new API endpoint:**
1. Edit `backend/app/api/photos.py`
2. FastAPI auto-reloads
3. Test at http://localhost:8000/docs

**Update database schema:**
1. Edit models in `backend/app/models/`
2. Create migration: `./scripts/migrate.sh create "description"`
3. Apply: `./scripts/migrate.sh upgrade`

**Change frontend styling:**
1. Edit CSS in `frontend/src/pages/*.css`
2. Vite HMR updates instantly

## 🐛 Troubleshooting

**Port already in use:**
```bash
docker-compose down
lsof -ti:8000 | xargs kill  # Kill process on 8000
```

**Database connection error:**
```bash
docker-compose restart postgres
docker-compose logs postgres
```

**Frontend won't start:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 📚 Learn More

- Architecture: `docs/architecture/system_architecture.md`
- API Spec: `docs/api/openapi.yaml`
- Security: `docs/security/security_privacy.md`
- Roadmap: `docs/roadmap.md`

## 🚢 Deploy to Production

1. Review `DEPLOYMENT_CHECKLIST.md`
2. Configure `infrastructure/terraform/terraform.tfvars`
3. Run `terraform apply`
4. Push to GitHub (triggers CI/CD)

---

**Need help?** Check the [Complete Walkthrough](file://.gemini/antigravity/brain/.../walkthrough.md)
