## [a06f890][V0.0.8]

### Features
- feat(pipeline-monitoring): Implement comprehensive pipeline monitoring system
- feat(pipeline-monitoring): Implement comprehensive pipeline monitoring system
- feat: Introduce automated changelog generation script and update the existing changelog and documentation workflow.

## [1a2e19a][V0.0.7]

### Features
- feat: Add environment variables for DB schema, S3 storage, and face recognition to production compose.
- feat: Add S3 configuration to the worker service, improve GCE deployment cleanup, and fix asyncio event loop handling in the thumbnail worker.
- feat: Add `is_admin` column to users, implement error handling and logging in people API endpoints, and refine the Alembic migration script.
- feat: Implement production Docker Compose setup, integrate it into the GCE deployment workflow, and enable/configure Celery worker.
- feat: Add `status`, `created_at`, and `user_id` indexes to the `admin_jobs` table.
- feat: add Alembic migration to create admin_job indexes.
- feat: Add .dockerignore, make web server port configurable, and improve Docker entrypoint robustness.
- feat: Offload clustering job processing to a new background task with dedicated session management and error handling.

### Fixes
- fix: correct session factory import name (AsyncSessionLocal)
- fix: remove unused db session parameter causing BackgroundTask silent failure
- fix: Enhance AdminDashboard data handling with array validation and enable sourcemaps in Vite build.

### Refactoring
- refactor: Extract application routes into `AppRoutes` component and integrate conditional animal routes directly.

### Chores
- chore: Refine frontend health check path and add production URL to allowed CORS origins.

### Other Changes
- debug: add test endpoint to call process_clustering_job directly
- debug: add synchronous celery broker connection test before BackgroundTask
- debug: add flush=True to all debug prints for Render visibility
- debug: add try/except logging around send_task() to diagnose silent broker failures
- ci: Add `docker-compose.prod.yml` to the paths-ignore list in the GCE build and deploy workflow.

## [05538bd][V0.0.6]

### Features
- feat: Add GitHub Actions workflows for building and deploying the worker and deploying Redis.
- feat: Add admin job management functionality, refactor worker deployment to use docker-compose, and update admin dashboard UI.
- feat: Implement feature flagging for animal detection, centralize CLIP model loading, and improve worker memory management.
- feat: Add AI model preloading to the worker startup script.
- feat: Enable direct model preloading for build processes and extend Celery broker timeouts to accommodate large model downloads.
- feat: Implement AI model preloading in Celery workers, configure HuggingFace cache, and update model loading parameters to disable safetensors.
- feat: Disable database connection pooling for Celery workers by setting `DATABASE_POOL_SIZE=0` and using `NullPool`.

### Fixes
- fix: Update Dockerfile.worker CMD to explicitly use bash and the full script path.
- fix: Safely display total users in admin dashboard and ensure legacy worker container cleanup during deployment.
- fix: Add defensive checks for potentially null or undefined arrays and dates before rendering in Admin Dashboard.
- fix: Set Celery `task_acks_late` to `False` to prevent Redis timeout issues.

### Refactoring
- refactor: update docker-compose commands to use new `docker compose` syntax
- refactor: Update API import path from utils to services.
- Refactor CLIP model loading to use a shared instance across scene and document classifiers, removing redundant loading logic from the thumbnail worker.
- Refactor: Streamline Cloudflare Worker SPA routing by removing security headers and explicit asset checks, and enhance Google Client ID validation.
- refactor: Standardize Docker network naming to `photobomb_app_net` and remove hardcoded Google Client ID fallback.

### Chores
- chore: specify execute permissions for `start_worker.sh` in the worker Dockerfile.

### Other Changes
- perf: Configure Celery to ignore task results for fire-and-forget operations.
- ci: Update Cloudflare deploy command to explicitly use `wrangler.json` for configuration.
- ci: Simplify deployment to use a Render deploy hook and add a frontend fallback for a missing Google Client ID.

## [53fa921][V0.0.5]

### Features
- feat: add workflow_dispatch trigger to frontend and backend deployment workflows
- feat: Ensure `.env` files end with a newline and automatically export sourced variables in GitHub Actions workflows.
- feat: Synthesize DATABASE_URL and JWT_SECRET_KEY in CI/CD workflows from existing variables if missing.
- feat: Ensure Docker network exists and improve deployment script discovery in the build workflow.
- feat: Set up deployment folder and consolidate .env file creation using a single secret in the deploy workflow.
- feat: Configure GCE worker deployment to use a secret-generated .env file and connect to the `photobomb_default` network, while ignoring GitHub deploy keys.
- feat: Standardize GCE deployment secret names, add worker image deployment to GCE, and enhance SSH setup documentation.
- feat: add imagehash dependency to backend requirements
- feat: Trigger worker image build workflow upon successful completion of base image build.

### Fixes
- fix: Normalize .env variable assignments and mask sensitive values in CI/CD debug output.
- fix: Remove carriage returns from .env files in deploy and build workflows and add debug output to worker image build.
- fix: Improve .env file sanitization in CI/CD workflows to handle case-insensitive exports, whitespace, and comments.
- fix: Sanitize generated .env files in CI/CD workflows and update worker deployment script path and network configuration.

### Refactoring
- refactor: Centralize .env file generation to the project root and pass host environment variables to Docker Compose services.
- refactor: Use `celery_app.send_task` for task dispatch in admin API and exclude API changes from triggering worker image builds.

### Chores
- chore: add external network definition for `photobomb_default`.

### Other Changes
- ci: Trigger deploy workflow on changes to `docker-compose.yml`.
- Remove postgres, redis, and worker services from docker-compose.yml and update API environment variables.
- Removed the Docker Compose version declaration, specified a worker image, and added `DATABASE_URL` to the worker service's environment variables.
- ci: exclude base requirements file from worker image build triggers and broaden job execution conditions for the worker image build job.

## [2154d0c][V0.0.4]

### Features
- feat: Add asgiref to worker requirements.
- feat: introduce Celery tasks for face and animal clustering, update the admin API to queue these tasks, enable the face worker in Celery imports, and add a task route for the db keepalive worker.
- feat: Add `timm` package to `Dockerfile.base` dependencies.
- feat(ci): Optimize Docker builds and add GitHub Actions
- feat: Allow listing hashtag photos using either a tag name or UUID identifier.
- feat: split services and optimize docker
- feat: Improve production process monitoring in `start_prod.sh` and add a legacy `process_upload` task alias in `thumbnail_worker.py`.
- feat: Implement heartbeat, concurrent uploads, and post-upload clustering, while refining photo processing to mark completion after AI analysis.
- feat: Decouple photo processing into initial metadata extraction and a separate AI analysis task.
- feat: implement direct photo sharing and fix hashtag processing
- feat: Introduce OCR text detection update base image
- feat: Enhance sharing flow and implement full keyboard accessibility
- feat: Add 'people' to photo tag categories and update rescan script to re-evaluate and force-update tag categories, including loading environment variables.

### Fixes
- fix: Update production VITE_API_URL to stable backend domain.
- fix: remove startCommand from render.yaml
- fix: Adjust component z-indices and update UserProfile to use `full_name` for display and enhanced initials generation.
- Fix: Adjust file re-upload logic to correctly handle cases where the file is already at its destination key.

### Chores
- chore: disable render worker, prep for GCE

### Other Changes
- config: Update production API URL to new Render domain.
- perf: Optimize thumbnail worker memory management and Celery concurrency, and improve timeline grid responsiveness on smaller screens.

## [dc45067][V0.0.3]

### Features
- feat: Configure Uvicorn with 10 workers, add configuration checks to various scripts, and update face clustering to process all users.
- feat: Add Cross-Origin-Opener-Policy header to responses.
- feat: Update Dockerfiles to use `python:3.11-slim` base, explicitly install `torch` and `torchvision` in the base image, and add a local Docker testing script.
- feat: update PyTorch base image to 2.5.1, refine system dependencies, and adjust Python package versions.
- feat: Introduce a custom Docker base image built via GitHub Actions to pre-install heavy dependencies, simplifying the main backend Dockerfile and accelerating builds.
- feat: Separate heavy machine learning dependencies into `requirements-base.txt` and install them in a dedicated Docker layer for improved build caching.

### Fixes
- fix(backend): deployment, thumbnails, and doc sync
- fix: Add idempotency checks to existing Alembic migrations for indexes and columns.

### Refactoring
- refactor: Lazily load heavy dependencies like transformers, numpy, and sklearn, and adjust production script worker configurations.
- refactor: replace hardcoded schema name with `settings.DB_SCHEMA` in index operations.
- refactor: make Alembic migrations idempotent by adding table existence checks before creating tables.
- refactor: remove CI/CD workflow and update the project name in wrangler.json.

### Chores
- chore: Reduce Celery worker concurrency and Uvicorn worker count in the production start script.
- chore: Adjust Uvicorn worker count from 10 to 4.
- chore: Tag base image with `v1` in the build workflow and update the backend Dockerfile to use the `v1` base image.
- chore: Update Dockerfile to use PyTorch CPU runtime and uv for dependency management, and make initial schema migration idempotent.

### Other Changes
- build: Update Dockerfile base image from `latest` to `v1` and remove platform specification.
- build: Specify `linux/amd64` platform for the Dockerfile base image.
- ci: remove push triggers from base image build workflow, making it manual-only.
- Update wrangler config name to photobomb

## [be0d5fe][V0.0.2]

### Features
- feat: Add `cmake` to backend Dockerfile, override frontend `react` and `react-dom` dependencies, and enable `legacy-peer-deps` in `.npmrc`.
- feat: overhaul gallery UI and unify hashtags system
- feat(hashtags): rebrand documents to hashtags and optimize performance
- feat: implement AI-powered photo intelligence and advanced sharing
- feat: add Alembic migration to update storage provider and backend values to S3.
- feat: Update compatibility date, add explicit assets binding, improve worker error logging, and include a debug header in responses.
- feat: Add `redeploy_frontend.sh` script to automate frontend build and Cloudflare Workers deployment.
- feat: add index for photos by user, storage provider, and taken at
- feat: Migrate backend storage to R2/S3 and fix background worker

### Fixes
- fix: Add `overrides` section to `package.json` to specify `@react-leaflet/core` version for `react-leaflet-cluster`.
- Fix COOP headers on SPA fallback routes
- Fix Google Sign-In COOP errors in production
- Fix: Add error handling to the SPA worker's asset fetching and ensure `.env` variables are sourced during frontend redeployment.

### Chores
- chore: configure selective CI/CD and fix Alembic migration
- chore: hardcode Google Client ID in main.jsx
- chore: Delete Netlify redirects file.
- chore: Add debug logging specific to migration failure

### Other Changes
- build: Add linear algebra development libraries and limit compilation threads to prevent OOM.
- Merge branch 'main' into qa
- style: Update button appearance in AlbumDetail and reduce masonry grid gutters in Timeline.

## [6269e57][V0.0.1]

### Features
- feat(frontend): improve filters, sorting, and zoom interaction
- feat: Add query analysis script and configure the database engine with unique prepared statement names.

### Fixes
- fix(deployment): secure fallback for /assets/ and fix meta tag warning
- fix(deployment): add SPA fallback worker and secure fallback logic
- fix(deployment): add SPA fallback worker to handle client-side routing
- fix(frontend): resolve ReferenceError in App.jsx
- fix(frontend): resolve zoom, auth redirect, and shared link issues
- fix: mobile upload crash and redirect auth users from login

### Refactoring
- refactor: Externalize Google Client ID to environment variables and update Vite configuration for dev options and cross-origin policy.

### Chores
- chore: update commit_check workflow logic

### Other Changes
- style(frontend): improve timeline spacing and modernize album detail UI
- _pgbouncer_statement_name
- zoomin, db error
- Configure database to use connection pooling and disable debug mode.
- redirecting
- _redirect
- thumb nail generation
- bug fixes
- deployment fix
- album sharing

## [bb1fb13][V0.0.0]

### Features
- feat: Implement photo selection, add to album, and trash features with new modals, pages, and updated UI.
- feat: Implement background photo uploads via service worker and optimize database indexes.
- feat: Add GitHub Actions workflow for production deployment.
- feat: Implement dynamic thumbnail generation with caching, refine photo action UI, and add GitHub deployment documentation.
- feat: Add project dependencies and initial Lightbox component styles.

### Fixes
- fix docker and requirements
- Fix Render configuration2
- Fix Render configuration

### Other Changes
- 3 bugs
- upload fix. v0
- service worker upload mime type
- missing icons
- missing env var
- added request
- googleauth added
- confguring urls binding fe and be
- render config
- added fly config
- wrangler config
- phase 2

