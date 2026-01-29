- [ ] **Environment Setup**
  - [ ] Cloudflare R2 account created
  - [ ] Bucket created (private)
  - [ ] R2 Access Keys generated (Edit permissions)
  - [ ] Credentials added to `backend/.env` (S3_ENDPOINT_URL, etc.)
  - [ ] Credentials added to `backend/.env`

- [ ] **Local Testing**
  - [ ] Docker and Docker Compose installed
  - [ ] Node.js 18+ installed
  - [ ] Backend started (`docker-compose up -d`)
  - [ ] Migrations run (`docker-compose exec api alembic upgrade head`)
  - [ ] Frontend dependencies installed (`cd frontend && npm install`)
  - [ ] Frontend running (`npm run dev`)
  - [ ] Registered test account
  - [ ] Uploaded test photo
  - [ ] Verified timeline displays photo

- [ ] **Code Review**
  - [ ] Security review complete
  - [ ] API endpoints tested
  - [ ] Database schema validated
  - [ ] Frontend UX reviewed
  - [ ] Mobile responsiveness tested

- [ ] **Pre-Production**
  - [ ] GCP project created
  - [ ] Terraform variables configured
  - [ ] SSL certificates ready
  - [ ] Domain DNS configured
  - [ ] Monitoring dashboards deployed
  - [ ] Backup strategy confirmed

- [ ] **Production Deployment**
  - [ ] Terraform infrastructure deployed (`terraform apply`)
  - [ ] Database migrations run on production
  - [ ] Environment variables set
  - [ ] CI/CD pipeline configured
  - [ ] Health checks passing
  - [ ] Smoke tests passed

- [ ] **Post-Launch**
  - [ ] Monitoring alerts configured
  - [ ] Error tracking active (Sentry)
  - [ ] Analytics setup (if needed)
  - [ ] Documentation published
  - [ ] Team onboarded
  - [ ] First user registered

- [ ] **Legal & Compliance**
  - [ ] Privacy Policy published
  - [ ] Terms of Service published
  - [ ] DMCA agent registered
  - [ ] GDPR compliance verified
  - [ ] Face recognition consent flow tested
